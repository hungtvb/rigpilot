"""Enforce budget, inventory, part ownership and explicit change consent."""
from rigpilot.catalog.models import CatalogSnapshot
from rigpilot.domain.models import BuildRequest, BuildSelection, ConstraintReport, ValidationIssue


def evaluate_constraints(
    request: BuildRequest, build: BuildSelection, snapshot: CatalogSnapshot
) -> ConstraintReport:
    items = {p.product_id: p for p in snapshot.products}
    issues: list[ValidationIssue] = []
    approval_required = False
    missing_price = False
    total = 0
    statuses = []
    owned_kinds = {x.kind for x in build.owned_components}
    owned_from_request = {x.kind: x.product_id for x in request.owned_components}

    def issue(code: str, severity: str, message: str, *product_ids: str):
        issues.append(ValidationIssue(code=code, severity=severity, message=message, affected_part_ids=tuple(product_ids)))

    for kind, locked_pid in request.locked_parts.items():
        selected = build.part_ids.get(kind)
        if selected != locked_pid:
            issue("LOCKED_PART_VIOLATION", "INCOMPATIBLE", f"Locked {kind} {locked_pid} must not be changed", locked_pid, *(selected,) if selected else ())

    for kind, product_id in build.part_ids.items():
        if product_id not in items or items[product_id].kind != kind:
            issue("PRODUCT_NOT_FOUND", "UNVERIFIED", f"Unknown {kind} product {product_id}", product_id)
        if kind in owned_kinds:
            if kind in owned_from_request and owned_from_request[kind] != product_id:
                issue("OWNED_PART_MISMATCH", "INCOMPATIBLE", "Ownership does not match selected part", product_id)
            continue
        offer = snapshot.offers.get(product_id)
        if offer is None:
            missing_price = True
            statuses.append("UNKNOWN")
            issue("OFFER_UNKNOWN", "UNVERIFIED", f"No shop offer for {product_id}", product_id)
            continue
        statuses.append(offer.stock)
        if offer.price_vnd is None:
            missing_price = True
            issue("PRICE_UNKNOWN", "UNVERIFIED", f"Price unavailable for {product_id}", product_id)
        else:
            total += offer.price_vnd
        if offer.stock == "UNKNOWN":
            issue("STOCK_UNKNOWN", "UNVERIFIED", f"Inventory unknown for {product_id}", product_id)
        elif offer.stock == "OUT_OF_STOCK":
            issue("OUT_OF_STOCK", "WARNING", f"Item is out of stock: {product_id}", product_id)

    for owned in build.owned_components:
        if owned.kind not in owned_from_request:
            issue("OWNERSHIP_UNCONFIRMED", "UNVERIFIED", f"Owned {owned.kind} not declared in request")
        elif owned.product_id != owned_from_request[owned.kind]:
            issue("OWNED_PART_MISMATCH", "INCOMPATIBLE", f"Owned {owned.kind} differs from request")

    if request.previous_parts:
        for kind, old_pid in request.previous_parts.items():
            new_pid = build.part_ids.get(kind)
            if new_pid and new_pid != old_pid:
                old = snapshot.offers.get(old_pid)
                if old is not None and old.stock == "OUT_OF_STOCK":
                    if (old_pid, new_pid) not in request.approved_replacements:
                        approval_required = True
                        issue("STOCKOUT_SUBSTITUTION_APPROVAL_REQUIRED", "APPROVAL_REQUIRED",
                              f"Approve replacement of out-of-stock {old_pid} with {new_pid}", old_pid, new_pid)

    if missing_price:
        total_purchase = None
    else:
        total_purchase = total
    budget_verified = total_purchase is not None and total_purchase <= request.budget_vnd
    if total_purchase is not None and total_purchase > request.budget_vnd:
        approval_required = True
        issue("OVER_BUDGET_APPROVAL_REQUIRED", "APPROVAL_REQUIRED",
              f"Total {total_purchase} VND exceeds budget {request.budget_vnd} VND")

    if "OUT_OF_STOCK" in statuses:
        stock_status = "OUT_OF_STOCK"
    elif "UNKNOWN" in statuses or not statuses:
        stock_status = "UNKNOWN"
    else:
        stock_status = "IN_STOCK"
    return ConstraintReport(total_purchase_vnd=total_purchase, budget_verified=budget_verified,
                            stock_status=stock_status, approval_required=approval_required, issues=tuple(issues))
