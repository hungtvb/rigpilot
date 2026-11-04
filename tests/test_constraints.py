from rigpilot.catalog.models import CatalogSnapshot, CatalogOffer
from rigpilot.domain.models import BuildRequest, BuildSelection, OwnedComponent
from rigpilot.domain.constraints import evaluate_constraints
from rigpilot.domain.compatibility import evaluate_compatibility
from test_compatibility import snapshot, selection


def request(**changes):
    data={"budget_vnd":25_000_000,"primary_workload":"gaming"}
    data.update(changes)
    return BuildRequest(**data)


def new_snapshot(**offers):
    original=snapshot()
    updates=original.offers.copy()
    for kind,fields in offers.items():
        pid=f"{kind}-1"
        updates[pid]=updates[pid].model_copy(update=fields)
    return CatalogSnapshot(snapshot_id=original.snapshot_id,products=original.products,offers=updates)


def codes(report):
    return {issue.code for issue in report.issues}


def test_owned_part_excluded_from_purchase_total():
    snap=new_snapshot()
    build=selection()
    owned=OwnedComponent(kind="gpu",product_id="gpu-1")
    build=BuildSelection(part_ids=build.part_ids,owned_components=(owned,))
    report=evaluate_constraints(request(owned_components=(owned,)),build,snap)
    assert report.total_purchase_vnd==7
    assert report.budget_verified


def test_unknown_owned_part_does_not_prove_compatibility():
    snap=new_snapshot()
    ids=selection().part_ids
    ids.pop("gpu")
    owned=OwnedComponent(kind="gpu",label="GeForce GPU, exact variant unknown")
    build=BuildSelection(part_ids=ids,owned_components=(owned,))
    constraints=evaluate_constraints(request(owned_components=(owned,)),build,snap)
    compatibility=evaluate_compatibility(build,snap)
    assert constraints.total_purchase_vnd == 7
    assert compatibility.status=="UNVERIFIED"


def test_missing_price_sets_budget_verified_false():
    report=evaluate_constraints(request(),selection(),new_snapshot(gpu={"price_vnd":None}))
    assert report.total_purchase_vnd is None and not report.budget_verified
    assert "PRICE_UNKNOWN" in codes(report)


def test_unknown_stock_never_becomes_in_stock():
    report=evaluate_constraints(request(),selection(),new_snapshot(gpu={"stock":"UNKNOWN"}))
    assert report.stock_status=="UNKNOWN" and "STOCK_UNKNOWN" in codes(report)


def test_unapproved_substitute_requires_specific_consent():
    snap=new_snapshot()
    old_gpu=snap.offers["gpu-1"].model_copy(update={"stock":"OUT_OF_STOCK"})
    snap=CatalogSnapshot(snapshot_id=snap.snapshot_id,products=snap.products,offers={**snap.offers,"gpu-1":old_gpu})
    new_gpu=snap.products[3].model_copy(update={"product_id":"gpu-2"})
    snap=CatalogSnapshot(snapshot_id=snap.snapshot_id,products=(*snap.products,new_gpu),offers={**snap.offers,"gpu-2":CatalogOffer(product_id="gpu-2",price_vnd=1,stock="IN_STOCK",snapshot_at="2026-11-04")})
    parts=selection().part_ids
    parts["gpu"]="gpu-2"
    report=evaluate_constraints(request(previous_parts={"gpu":"gpu-1"}),BuildSelection(part_ids=parts),snap)
    assert report.approval_required and "STOCKOUT_SUBSTITUTION_APPROVAL_REQUIRED" in codes(report)


def test_approval_for_different_gpu_not_accepted():
    snap=new_snapshot(gpu={"stock":"OUT_OF_STOCK"})
    parts=selection().part_ids
    parts["gpu"]="gpu-2"
    report=evaluate_constraints(request(previous_parts={"gpu":"gpu-1"},approved_replacements=(("gpu-1","gpu-3"),)),BuildSelection(part_ids=parts),snap)
    assert report.approval_required


def test_locked_product_cannot_be_replaced():
    report=evaluate_constraints(request(locked_parts={"cpu":"cpu-locked"}),selection(),new_snapshot())
    assert "LOCKED_PART_VIOLATION" in codes(report)


def test_over_budget_requires_explicit_decision():
    report=evaluate_constraints(request(budget_vnd=1),selection(),new_snapshot())
    assert report.approval_required and not report.budget_verified
    assert "OVER_BUDGET_APPROVAL_REQUIRED" in codes(report)
