"""Budget, stock, ownership, hard locks, and pair-specific stockout consent."""
from __future__ import annotations

from rigpilot.catalog.models import CatalogSnapshot
from .models import BuildRequest, BuildSelection, ConstraintReport, ValidationIssue


def evaluate_constraints(request: BuildRequest, build: BuildSelection, snapshot: CatalogSnapshot) -> ConstraintReport:
    product_map={p.product_id:p for p in snapshot.products}
    issues=[]
    approval_required=False

    def report(code: str, reason: str, *ids: str, error: bool=False):
        issues.append(ValidationIssue(code=code,severity='ERROR' if error else 'WARNING',affected_part_ids=tuple(ids),message=reason))

    if set(request.owned_components) != set(build.owned_components):
        report('OWNED_PART_SET_MISMATCH','Selected owned components must match request-owned components',error=True)

    for kind,required_id in request.locked_parts.items():
        found=build.part_ids.get(kind)
        if found is None:
            found=next((p.product_id for p in build.owned_components if p.kind==kind),None)
        if found!=required_id:
            report('LOCKED_PART_CHANGED',f'{kind} must retain locked product {required_id}',required_id,found or 'missing',error=True)

    if request.previous_parts:
        for kind,old_id in request.previous_parts.items():
            selected_id=build.part_ids.get(kind)
            if selected_id is None:
                selected_id=next((p.product_id for p in build.owned_components if p.kind==kind),None)
            old_offer=snapshot.offers.get(old_id)
            if selected_id!=old_id and (old_offer is None or old_offer.stock=='OUT_OF_STOCK'):
                if (old_id,selected_id) not in request.approved_replacements:
                    if old_offer is None:
                        report('PREVIOUS_PART_UNAVAILABLE_APPROVAL_REQUIRED',
                               f'Previous {old_id} is absent from the current catalog; replacing it with {selected_id} requires approval',
                               old_id,selected_id or 'missing',error=True)
                    else:
                        report('STOCKOUT_SUBSTITUTION_APPROVAL_REQUIRED',
                               f'Substituting out-of-stock {old_id} requires approval for {selected_id}',
                               old_id,selected_id or 'missing',error=True)
                    approval_required=True

    total=0
    any_missing_price=False
    stocks=[]
    for kind, product_id in build.part_ids.items():
        product=product_map.get(product_id)
        offer=snapshot.offers.get(product_id)
        if product is None or product.kind!=kind or offer is None:
            report('UNKNOWN_PURCHASE_ITEM',f'Cannot verify purchased {kind}: {product_id}',product_id,error=True)
            any_missing_price=True
            stocks.append('UNKNOWN')
            continue
        stocks.append(offer.stock)
        if offer.stock=='OUT_OF_STOCK':
            report('STOCK_OUT',f'{product_id} is out of stock',product_id)
        elif offer.stock=='UNKNOWN':
            report('STOCK_UNKNOWN',f'{product_id} stock is unverified',product_id)
        if offer.price_vnd is None:
            any_missing_price=True
            report('PRICE_UNKNOWN',f'{product_id} has no verified synthetic price',product_id,error=True)
        else:
            total+=offer.price_vnd

    for owned in build.owned_components:
        if owned.product_id is not None and owned.product_id not in product_map:
            report('OWNED_PART_UNKNOWN',f'Owned {owned.kind} is not in catalog; compatibility remains unknown',owned.product_id)

    amount=None if any_missing_price else total
    if amount is not None and amount>request.budget_vnd:
        report('OVER_BUDGET',f'Purchase total {amount} VND exceeds budget {request.budget_vnd} VND',error=True)
    if 'OUT_OF_STOCK' in stocks:
        stock='OUT_OF_STOCK'
    elif 'UNKNOWN' in stocks:
        stock='UNKNOWN'
    else:
        stock='IN_STOCK'
    budget_verified=(amount is not None and amount<=request.budget_vnd and not any(i.severity=='ERROR' for i in issues))
    return ConstraintReport(total_purchase_vnd=amount,budget_verified=budget_verified,stock_status=stock,approval_required=approval_required,issues=tuple(issues))
