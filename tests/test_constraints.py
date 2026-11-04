from rigpilot.catalog.models import CatalogItem, CatalogOffer, CatalogSnapshot
from rigpilot.domain.models import BuildRequest, BuildSelection, OwnedComponent
from rigpilot.domain.constraints import evaluate_constraints
from rigpilot.domain.compatibility import evaluate_compatibility


def fixture(*, gpu_price=7000000, gpu_stock='IN_STOCK', old_gpu_stock='OUT_OF_STOCK'):
    products=[
        CatalogItem(product_id='cpu',kind='cpu',brand='T',model='CPU',specs={'socket':'AM5','memory_type':'DDR5','tdp_w':65}),
        CatalogItem(product_id='gpu',kind='gpu',brand='T',model='GPU',specs={'length_mm':200,'board_power_w':120,'power_connectors':['8-pin']}),
        CatalogItem(product_id='old-gpu',kind='gpu',brand='T',model='Old GPU',specs={'length_mm':270,'board_power_w':150,'power_connectors':['8-pin']}),
        CatalogItem(product_id='case',kind='case',brand='T',model='Case',specs={'supported_form_factors':['mATX'],'max_gpu_length_mm':420}),
    ]
    offers={p.product_id:CatalogOffer(product_id=p.product_id,price_vnd={'cpu':3000000,'gpu':gpu_price,'old-gpu':6000000,'case':1000000}[p.product_id],stock={'gpu':gpu_stock,'old-gpu':old_gpu_stock}.get(p.product_id,'IN_STOCK'),snapshot_at='2026-11-04') for p in products}
    return CatalogSnapshot(snapshot_id='test',products=tuple(products),offers=offers)


def req(**kwargs):
    return BuildRequest(budget_vnd=15000000,primary_workload='gaming',**kwargs)


def build(**kwargs):
    return BuildSelection(part_ids={'cpu':'cpu','gpu':'gpu','case':'case'},owned_components=(),**kwargs)


def issue_codes(report):
    return {i.code for i in report.issues}


def test_owned_part_excluded_from_purchase_total():
    request=req(owned_components=(OwnedComponent(kind='gpu',product_id='gpu'),))
    selection=BuildSelection(part_ids={'cpu':'cpu','case':'case'},owned_components=request.owned_components)
    result=evaluate_constraints(request,selection,fixture())
    assert result.total_purchase_vnd==4000000
    assert result.budget_verified


def test_unknown_owned_part_does_not_prove_compatibility():
    request=req(owned_components=(OwnedComponent(kind='gpu',label='old graphics card'),))
    selection=BuildSelection(part_ids={'cpu':'cpu','case':'case'},owned_components=request.owned_components)
    result=evaluate_compatibility(selection,fixture())
    assert result.status=='UNVERIFIED'


def test_missing_price_sets_budget_verified_false():
    result=evaluate_constraints(req(),build(),fixture(gpu_price=None))
    assert result.total_purchase_vnd is None
    assert not result.budget_verified
    assert 'PRICE_UNKNOWN' in issue_codes(result)


def test_unknown_stock_never_becomes_in_stock():
    result=evaluate_constraints(req(),build(),fixture(gpu_stock='UNKNOWN'))
    assert result.stock_status=='UNKNOWN'
    assert 'STOCK_UNKNOWN' in issue_codes(result)


def test_unapproved_substitute_requires_specific_consent():
    request=req(previous_parts={'gpu':'old-gpu'})
    result=evaluate_constraints(request,build(),fixture())
    assert result.approval_required
    assert 'STOCKOUT_SUBSTITUTION_APPROVAL_REQUIRED' in issue_codes(result)


def test_approval_for_different_gpu_not_accepted():
    request=req(previous_parts={'gpu':'old-gpu'},approved_replacements=(('old-gpu','wrong-gpu'),))
    result=evaluate_constraints(request,build(),fixture())
    assert result.approval_required


def test_locked_product_cannot_be_replaced():
    request=req(locked_parts={'gpu':'old-gpu'})
    result=evaluate_constraints(request,build(),fixture())
    assert 'LOCKED_PART_CHANGED' in issue_codes(result)
    assert not result.budget_verified


def test_over_budget_requires_explicit_decision():
    result=evaluate_constraints(BuildRequest(budget_vnd=9000000,primary_workload='gaming'),build(),fixture())
    assert result.total_purchase_vnd==11000000
    assert not result.budget_verified
    assert 'OVER_BUDGET' in issue_codes(result)


def test_matching_exact_substitution_permission_is_accepted():
    request=req(previous_parts={'gpu':'old-gpu'},approved_replacements=(('old-gpu','gpu'),))
    result=evaluate_constraints(request,build(),fixture())
    assert not result.approval_required
    assert result.budget_verified


def test_removed_previous_product_cannot_be_silently_replaced():
    # The customer's old GPU is absent from the latest catalog snapshot:
    # lack of a current offer is not permission to replace their selection.
    request = req(previous_parts={'gpu': 'previous-gpu-no-longer-listed'})
    result = evaluate_constraints(request, build(), fixture())
    assert result.approval_required
    assert 'STOCKOUT_SUBSTITUTION_APPROVAL_REQUIRED' in issue_codes(result)
