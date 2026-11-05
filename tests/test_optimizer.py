from dataclasses import replace
from rigpilot.catalog.models import CatalogItem, CatalogOffer, CatalogSnapshot
from rigpilot.domain.models import BuildRequest, OwnedComponent
from rigpilot.domain.optimizer import optimize_build


def snapshot(*, gpu_alternative=True, unknown_gpu_price=False, missing_kind=None, old_gpu_stock='IN_STOCK'):
    specs={
        'cpu': {'socket':'AM5','memory_type':'DDR5','tdp_w':65},
        'motherboard': {'socket':'AM5','memory_type':'DDR5','form_factor':'mATX','m2_slots':2},
        'ram': {'memory_type':'DDR5'},
        'storage': {'interface':'M.2 NVMe PCIe 4.0 x4'},
        'gpu': {'length_mm':200,'board_power_w':120,'power_connectors':['8-pin']},
        'psu': {'rated_w':750,'connectors':['PCIe-8-pin']},
        'case': {'supported_form_factors':['mATX'],'max_gpu_length_mm':350,'max_cooler_height_mm':170},
        'cooler': {'supported_sockets':['AM5'],'height_mm':150},
    }
    products=[]
    offers={}
    for kind,dimensions in specs.items():
        if kind==missing_kind:
            continue
        pid=f'{kind}-1'
        tier={'gaming':2,'creator':1}
        price=1000000 if kind!='gpu' else 5000000
        if kind=='gpu' and unknown_gpu_price:
            price=None
        products.append(CatalogItem(product_id=pid,kind=kind,brand='T',model=pid,specs=dimensions,workload_fit_tier=tier,fit_evidence_ids={'gaming':['curated-qualitative-ranking'],'creator':['curated-qualitative-ranking']}))
        offers[pid]=CatalogOffer(product_id=pid,price_vnd=price,stock=old_gpu_stock if kind=='gpu' else 'IN_STOCK',snapshot_at='2026-11-04')
    if gpu_alternative:
        products.append(CatalogItem(product_id='gpu-2',kind='gpu',brand='T',model='gpu-2',specs=specs['gpu'],workload_fit_tier={'gaming':3,'creator':0},fit_evidence_ids={'gaming':['curated-qualitative-ranking'],'creator':['curated-qualitative-ranking']}))
        offers['gpu-2']=CatalogOffer(product_id='gpu-2',price_vnd=6500000,stock='IN_STOCK',snapshot_at='2026-11-04')
    return CatalogSnapshot(snapshot_id='test',products=tuple(products),offers=offers)


def request(**kwargs):
    return BuildRequest(budget_vnd=16000000,primary_workload='gaming',**kwargs)


def test_unverified_primary_workload_tier_cannot_override_lower_price():
    result=optimize_build(request(secondary_workloads=('creator',)),snapshot())
    assert result.selected.part_ids['gpu']=='gpu-1'
    assert result.status=='PROVISIONAL'


def test_same_fit_tier_prefers_lower_price():
    data=snapshot()
    p=tuple(item.model_copy(update={'workload_fit_tier': {'gaming': 2,'creator':1}}) if item.product_id=='gpu-2' else item for item in data.products)
    result=optimize_build(request(),data.model_copy(update={'products':p}))
    assert result.selected.part_ids['gpu']=='gpu-1'
    assert result.status=='PROVISIONAL'


def test_owned_gpu_remains_in_candidate():
    owned=OwnedComponent(kind='gpu',product_id='gpu-1')
    result=optimize_build(request(owned_components=(owned,)),snapshot())
    assert 'gpu' not in result.selected.part_ids
    assert result.selected.owned_components==(owned,)
    assert result.constraints.total_purchase_vnd==7000000


def test_locked_cpu_never_changes():
    result=optimize_build(request(locked_parts={'cpu':'cpu-1'}),snapshot())
    assert result.selected.part_ids['cpu']=='cpu-1'
    missing=optimize_build(request(locked_parts={'cpu':'not-in-catalog'}),snapshot())
    assert missing.status=='NO_CANDIDATE'


def test_missing_price_cannot_yield_recommended():
    result=optimize_build(request(),snapshot(gpu_alternative=False,unknown_gpu_price=True))
    assert result.status=='PROVISIONAL'
    assert result.constraints.total_purchase_vnd is None


def test_unapproved_stockout_replacement_requires_approval():
    result=optimize_build(request(previous_parts={'gpu':'gpu-1'}),snapshot(old_gpu_stock='OUT_OF_STOCK'))
    assert result.status=='APPROVAL_REQUIRED'
    assert result.selected.part_ids['gpu']=='gpu-2'


def test_evaluation_cap_marks_selection_limited():
    result=optimize_build(request(),snapshot(),max_evaluations=1)
    assert result.selection_limited
    assert result.status=='PROVISIONAL'
    assert 'not exhaustive' in ' '.join(result.explanation).lower()


def test_no_viable_candidate_is_explicit():
    result=optimize_build(request(),snapshot(missing_kind='motherboard'))
    assert result.status=='NO_CANDIDATE'
    assert result.selected is None


def test_over_budget_returns_warned_closest_build():
    result=optimize_build(BuildRequest(budget_vnd=1000000,primary_workload='gaming'),snapshot(gpu_alternative=False))
    assert result.status=='PROVISIONAL'
    assert 'OVER_BUDGET' in {issue.code for issue in result.constraints.issues}


def test_no_unsourced_fps_claims_in_explanation():
    result=optimize_build(request(),snapshot())
    assert 'fps' not in ' '.join(result.explanation).lower()


def test_unverified_catalog_evidence_ids_do_not_certify_a_build():
    # Strings in imported JSON are not validated source records.
    # This fixture has no trusted benchmark/provenance registry.
    result = optimize_build(request(), snapshot(gpu_alternative=False))
    assert result.compatibility.status == 'COMPATIBLE'
    assert result.constraints.budget_verified
    assert result.status == 'PROVISIONAL'
    assert result.evidence_ids == ()
    assert 'unverified' in ' '.join(result.explanation).lower()


def test_no_feasible_budget_build_picks_nearest_overspend():
    # All combinations are over 1M. The lower-priced GPU is 5M;
    # an unsupported extra fit tier on the 6.5M GPU must not increase overspend.
    result = optimize_build(
        BuildRequest(budget_vnd=1_000_000, primary_workload='gaming'),
        snapshot(),
    )
    assert result.status == 'PROVISIONAL'
    assert result.selected.part_ids['gpu'] == 'gpu-1'
    assert result.constraints.total_purchase_vnd == 12_000_000
    assert 'OVER_BUDGET' in {i.code for i in result.constraints.issues}


def test_unverified_workload_tiers_do_not_justify_more_expensive_choice():
    # Imported qualitative tiers and arbitrary evidence-ID strings are not
    # verified benchmark records. They must not justify a 1.5M premium.
    result = optimize_build(request(), snapshot())
    assert result.status == 'PROVISIONAL'
    assert result.evidence_ids == ()
    assert result.selected.part_ids['gpu'] == 'gpu-1'
    assert result.constraints.total_purchase_vnd == 12_000_000
