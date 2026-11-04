"""Bounded, evidence-aware candidate ranking without invented performance metrics."""
from itertools import product

from rigpilot.catalog.models import CatalogItem, CatalogSnapshot
from rigpilot.domain.compatibility import evaluate_compatibility
from rigpilot.domain.constraints import evaluate_constraints
from rigpilot.domain.models import BuildRequest, BuildSelection, RecommendationResult

_KINDS = ("cpu", "motherboard", "ram", "gpu", "storage", "psu", "case", "cooler")


def optimize_build(request: BuildRequest, snapshot: CatalogSnapshot, max_evaluations: int = 5000) -> RecommendationResult:
    if max_evaluations <= 0:
        raise ValueError("max_evaluations must be positive")
    by_id: dict[str, CatalogItem] = {p.product_id: p for p in snapshot.products}
    owned = {o.kind: o for o in request.owned_components}
    options: list[list[str | None]] = []
    for kind in _KINDS:
        if kind in owned:
            pid = owned[kind].product_id
            options.append([pid] if pid else [None])
        elif kind in request.locked_parts:
            options.append([request.locked_parts[kind]])
        else:
            candidates = sorted(p.product_id for p in snapshot.products if p.kind == kind)
            if not candidates:
                return RecommendationResult(status="NO_CANDIDATE", selected=None, compatibility=None,
                    constraints=None, explanation=(f"Missing purchasable {kind} in catalog",))
            options.append(candidates)

    best = None
    best_score = None
    evaluated = 0
    limited = False
    for group in product(*options):
        if evaluated >= max_evaluations:
            limited = True
            break
        evaluated += 1
        chosen = BuildSelection(part_ids={kind: pid for kind, pid in zip(_KINDS, group) if pid is not None},
                                owned_components=request.owned_components)
        compatibility = evaluate_compatibility(chosen, snapshot)
        constraints = evaluate_constraints(request, chosen, snapshot)
        parts = [by_id[pid] for pid in group if pid in by_id and pid is not None]
        primary_fit = sum(p.workload_fit_tier.get(request.primary_workload, 0) for p in parts)
        secondary_fit = sum(p.workload_fit_tier.get(w, 0) for p in parts for w in request.secondary_workloads)
        evidence_ids = tuple(sorted(set(eid for p in parts for eid in
            p.fit_evidence_ids.get(request.primary_workload, ()))))
        hard_ok = compatibility.status != "INCOMPATIBLE" and not any(
            i.severity == "INCOMPATIBLE" for i in constraints.issues)
        score = (
            int(hard_ok),
            int(constraints.budget_verified),
            int(constraints.stock_status == "IN_STOCK"),
            int(not constraints.approval_required),
            int(compatibility.status == "COMPATIBLE"),
            primary_fit,
            secondary_fit,
            int(bool(evidence_ids)),
            -(constraints.total_purchase_vnd if constraints.total_purchase_vnd is not None else 10**18),
            tuple(group_item or "" for group_item in group),
        )
        if best_score is None or score > best_score:
            best_score = score
            best = (chosen, compatibility, constraints, evidence_ids)

    if best is None:
        return RecommendationResult(status="NO_CANDIDATE", selected=None, compatibility=None,
            constraints=None, selection_limited=limited, explanation=("No candidate could be evaluated",))

    chosen, compatibility, constraints, evidence_ids = best
    if constraints.approval_required:
        status = "APPROVAL_REQUIRED"
    elif limited or compatibility.status != "COMPATIBLE" or not constraints.budget_verified or \
            constraints.stock_status != "IN_STOCK" or not evidence_ids or any(
                x.severity in ("INCOMPATIBLE", "UNVERIFIED") for x in constraints.issues):
        status = "PROVISIONAL"
    else:
        status = "RECOMMENDED"
    notes = ["Choice ranks evaluated catalog combinations under the user's primary workload and budget.",
             "Qualitative fit tiers are not measured FPS or a proof of global optimality."]
    if limited:
        notes.append("Candidate enumeration capped; optimum is not proven.")
    if not evidence_ids:
        notes.append("No reviewed workload-fit evidence is available for this selection.")
    if compatibility.status == "INCOMPATIBLE":
        notes.append("Known incompatible parts: this selection is NOT a working PC.")
    if constraints.approval_required:
        notes.append("Customer approval required before applying the proposed changes.")
    return RecommendationResult(status=status, selected=chosen, compatibility=compatibility,
        constraints=constraints, evidence_ids=evidence_ids, selection_limited=limited, explanation=tuple(notes))
