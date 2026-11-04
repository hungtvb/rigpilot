from rigpilot.catalog.models import CatalogSnapshot, CatalogOffer
from rigpilot.domain.models import BuildRequest, OwnedComponent
from rigpilot.domain.optimizer import optimize_build
from test_compatibility import snapshot


def req(**kwargs):
    fields={"budget_vnd":30_000_000,"primary_workload":"gaming"}
    fields.update(kwargs)
    return BuildRequest(**fields)


def with_gpu_options(original=None, *, second_price=2, primary=(3,1), secondary=(1,3)):
    original=original or snapshot()
    gpu=next(p for p in original.products if p.kind=="gpu")
    g1=gpu.model_copy(update={"workload_fit_tier":{"gaming":primary[0],"creator":secondary[0]},"fit_evidence_ids":{"gaming":["fixture-a"],"creator":["fixture-a"]}})
    g2=gpu.model_copy(update={"product_id":"gpu-2","model":"fixture-GPU-2","workload_fit_tier":{"gaming":primary[1],"creator":secondary[1]},"fit_evidence_ids":{"gaming":["fixture-b"],"creator":["fixture-b"]}})
    items=tuple(g1 if p.kind=="gpu" else p for p in original.products)+(g2,)
    offers={**original.offers,"gpu-2":CatalogOffer(product_id="gpu-2",price_vnd=second_price,stock="IN_STOCK",snapshot_at="2026-11-04")}
    return CatalogSnapshot(snapshot_id="test",products=items,offers=offers)


def test_primary_workload_beats_secondary_when_constraints_equal():
    r=optimize_build(req(secondary_workloads=("creator",)),with_gpu_options())
    assert r.selected.part_ids["gpu"]=="gpu-1"


def test_same_fit_tier_prefers_lower_price():
    snap=with_gpu_options(primary=(2,2),secondary=(1,1),second_price=0)
    r=optimize_build(req(),snap)
    assert r.selected.part_ids["gpu"]=="gpu-2"


def test_owned_gpu_remains_in_candidate():
    owned=OwnedComponent(kind="gpu",product_id="gpu-1")
    result=optimize_build(req(owned_components=(owned,)),with_gpu_options())
    assert result.selected.part_ids["gpu"]=="gpu-1"
    assert result.constraints.total_purchase_vnd==7


def test_locked_cpu_never_changes():
    result=optimize_build(req(locked_parts={"cpu":"cpu-1"}),with_gpu_options())
    assert result.selected.part_ids["cpu"]=="cpu-1"


def test_missing_price_cannot_yield_recommended():
    s=with_gpu_options()
    offers={**s.offers,"cpu-1":s.offers["cpu-1"].model_copy(update={"price_vnd":None})}
    result=optimize_build(req(),CatalogSnapshot(snapshot_id=s.snapshot_id,products=s.products,offers=offers))
    assert result.status!="RECOMMENDED" and result.constraints.total_purchase_vnd is None


def test_unapproved_stockout_replacement_requires_approval():
    s=with_gpu_options()
    offers={**s.offers,"gpu-1":s.offers["gpu-1"].model_copy(update={"stock":"OUT_OF_STOCK"})}
    s=CatalogSnapshot(snapshot_id=s.snapshot_id,products=s.products,offers=offers)
    result=optimize_build(req(previous_parts={"gpu":"gpu-1"}),s)
    assert result.selected.part_ids["gpu"]=="gpu-2"
    assert result.status=="APPROVAL_REQUIRED" and result.constraints.approval_required


def test_evaluation_cap_marks_selection_limited():
    r=optimize_build(req(),with_gpu_options(),max_evaluations=1)
    assert r.selection_limited and r.status=="PROVISIONAL"


def test_no_viable_candidate_is_explicit():
    full=snapshot()
    only=CatalogSnapshot(snapshot_id="empty-gpu",products=tuple(p for p in full.products if p.kind!="gpu"),offers={k:v for k,v in full.offers.items() if k!="gpu-1"})
    r=optimize_build(req(),only)
    assert r.status=="NO_CANDIDATE" and r.selected is None


def test_missing_qualitative_evidence_is_provisional():
    result=optimize_build(req(),snapshot())
    assert result.status=="PROVISIONAL"
