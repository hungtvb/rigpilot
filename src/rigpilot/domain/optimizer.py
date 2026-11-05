"""Bounded, explainable value-first candidate search (not global optimality)."""
from __future__ import annotations

from itertools import product

from rigpilot.catalog.models import CatalogItem, CatalogSnapshot
from .compatibility import evaluate_compatibility
from .constraints import evaluate_constraints
from .models import BuildRequest, BuildSelection, RecommendationResult, REQUIRED_COMPONENT_KINDS


def optimize_build(request: BuildRequest, snapshot: CatalogSnapshot, max_evaluations: int = 5000) -> RecommendationResult:
    if max_evaluations < 1:
        raise ValueError('max_evaluations must be positive')
    by_kind: dict[str,list[CatalogItem]]={k:[] for k in REQUIRED_COMPONENT_KINDS}
    by_id = {part.product_id:part for part in snapshot.products}
    owned = {part.kind:part for part in request.owned_components}
    for item in snapshot.products:
        if item.kind in by_kind:
            by_kind[item.kind].append(item)
    required_kinds=[k for k in REQUIRED_COMPONENT_KINDS if k not in owned]
    candidate_choices=[]
    for kind in required_kinds:
        choices=sorted(by_kind[kind],key=lambda x:x.product_id)
        if kind in request.locked_parts:
            choices=[p for p in choices if p.product_id == request.locked_parts[kind]]
        if not choices:
            return RecommendationResult(status='NO_CANDIDATE',explanation=(f'No catalog item for required component kind {kind} with current locks.',))
        candidate_choices.append(choices)
    for kind,part in owned.items():
        if kind in request.locked_parts and part.product_id!=request.locked_parts[kind]:
            return RecommendationResult(status='NO_CANDIDATE',explanation=(f'Owned {kind} conflicts with locked product ID.',))

    results=[]
    count=0
    truncated=False
    for combo in product(*candidate_choices):
        if count >= max_evaluations:
            truncated=True
            break
        count += 1
        selection = BuildSelection(part_ids={kind:item.product_id for kind,item in zip(required_kinds,combo)},owned_components=request.owned_components)
        compat=evaluate_compatibility(selection,snapshot)
        rules=evaluate_constraints(request,selection,snapshot)
        parts=list(combo)+[by_id[x.product_id] for x in request.owned_components if x.product_id in by_id]
        # Tiers are *curated ordinal fit annotations*, never measured FPS.
        primary=sum(p.workload_fit_tier.get(request.primary_workload,0) for p in parts)
        secondary=sum(p.workload_fit_tier.get(w,0) for w in request.secondary_workloads for p in parts)
        # Imported fit_evidence_ids are unchecked strings; no provenance registry
        # exists in this core slice. Do not certify or expose them as citations.
        # Verified evidence will be wired in the future knowledge/RAG slice.
        citations: tuple[str, ...] = ()
        fits_sourced = False
        in_budget = rules.total_purchase_vnd is not None and rules.total_purchase_vnd <= request.budget_vnd
        compatible = compat.status=='COMPATIBLE'
        stock_ok = rules.stock_status=='IN_STOCK'
        other_errors=any(i.severity=='ERROR' and i.code not in ('STOCKOUT_SUBSTITUTION_APPROVAL_REQUIRED', 'PREVIOUS_PART_UNAVAILABLE_APPROVAL_REQUIRED') for i in rules.issues)
        if compatible and stock_ok and in_budget and not other_errors:
            group=1 if rules.approval_required else 0
        elif compat.status=='INCOMPATIBLE':
            group=4
        elif not in_budget:
            group=3
        else:
            group=2
        # Deterministic tie-breakers and no float/unsupported FPS arithmetic.
        cost=rules.total_purchase_vnd if rules.total_purchase_vnd is not None else 10**18
        # When every feasible purchase exceeds budget, the least overspend is
        # the nearest non-compliant alternative. Never pay more merely because
        # unverified qualitative workload tiers claim an advantage.
        # Qualitative fit labels in this core are unverified catalog metadata.
        # They must not justify spending more without a trusted source registry.
        trusted_primary = primary if fits_sourced else 0
        trusted_secondary = secondary if fits_sourced else 0
        if group == 3:
            rank=(group,cost,-trusted_primary,-trusted_secondary,tuple(x.product_id for x in combo))
        else:
            rank=(group,-trusted_primary,-trusted_secondary,cost,tuple(x.product_id for x in combo))
        results.append((rank,selection,compat,rules,citations,fits_sourced))
    if not results:
        return RecommendationResult(status='NO_CANDIDATE',explanation=('No combination could be assessed.',))
    results.sort(key=lambda x:x[0])
    _,best,compat,rules,citations,fits_sourced=results[0]
    warnings=tuple(i.code for i in (*compat.issues,*rules.issues))
    if rules.approval_required:
        status='APPROVAL_REQUIRED'
    elif compat.status=='COMPATIBLE' and rules.budget_verified and rules.stock_status=='IN_STOCK' and fits_sourced and not truncated:
        status='RECOMMENDED'
    else:
        status='PROVISIONAL'
    explanation=['Selected from candidates satisfying checked constraints; performance ordering is provisional without verified workload evidence.']
    if truncated:
        explanation.append('Candidate search is not exhaustive; evaluation cap reached.')
    if not fits_sourced:
        explanation.append('Workload evidence IDs are unverified; selection is provisional.')
    if warnings:
        explanation.append('Unresolved checks: '+', '.join(warnings)+'.')
    if compat.status=='INCOMPATIBLE':
        explanation.append('Known incompatible parts: this build is not certified to operate.')
    if rules.approval_required:
        explanation.append('Customer must approve the exact out-of-stock substitution before applying it.')
    return RecommendationResult(status=status,selected=best,compatibility=compat,constraints=rules,evidence_ids=citations,selection_limited=truncated,explanation=tuple(explanation))
