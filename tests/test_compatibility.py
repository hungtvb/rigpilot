from rigpilot.catalog.models import CatalogItem, CatalogOffer, CatalogSnapshot
from rigpilot.domain.models import BuildSelection, OwnedComponent
from rigpilot.domain.compatibility import evaluate_compatibility


def catalog(*, cpu_socket='AM5', board_socket='AM5', ram_type='DDR5', board_ram='DDR5', gpu_length=199, case_gpu=410, gpu_connectors=('8-pin',), psu_connectors=('8-pin',), psu_watts=750, board_form_factor='mATX', case_factors=('mATX', 'ATX'), cooler_height=150, case_cooler_height=170, omit=()):
    base = [
        ('cpu','cpu',{'socket': cpu_socket, 'memory_type':'DDR5','tdp_w':65}),
        ('board','motherboard',{'socket': board_socket, 'memory_type':board_ram,'form_factor':board_form_factor,'m2_slots':2}),
        ('memory','ram',{'memory_type':ram_type}),
        ('video','gpu',{'length_mm':gpu_length,'board_power_w':120,'power_connectors':list(gpu_connectors)}),
        ('disk','storage',{'interface':'M.2 NVMe PCIe 4.0 x4'}),
        ('supply','psu',{'rated_w':psu_watts,'connectors':list(psu_connectors)}),
        ('chassis','case',{'supported_form_factors':list(case_factors),'max_gpu_length_mm':case_gpu,'max_cooler_height_mm':case_cooler_height}),
        ('fan','cooler',{'supported_sockets':['AM5','LGA1700'],'height_mm':cooler_height}),
    ]
    products=[]
    for identifier,kind,specs in base:
        for field in omit:
            if field.startswith(identifier+'.'):
                specs.pop(field.split('.',1)[1],None)
        products.append(CatalogItem(product_id=identifier,kind=kind,brand='Test',model=identifier,specs=specs))
    return CatalogSnapshot(snapshot_id='test',products=tuple(products),offers={i.product_id:CatalogOffer(product_id=i.product_id,price_vnd=100,stock='IN_STOCK',snapshot_at='2026-11-04') for i in products})


def selection(**overrides):
    parts={'cpu':'cpu','motherboard':'board','ram':'memory','gpu':'video','storage':'disk','psu':'supply','case':'chassis','cooler':'fan'}
    parts.update(overrides)
    return BuildSelection(part_ids=parts, owned_components=())


def test_socket_conflict_is_incompatible():
    result=evaluate_compatibility(selection(),catalog(board_socket='LGA1700'))
    assert result.status=='INCOMPATIBLE'
    assert 'CPU_SOCKET_MISMATCH' in {i.code for i in result.issues}


def test_ram_generation_conflict_is_incompatible():
    result=evaluate_compatibility(selection(),catalog(ram_type='DDR4'))
    assert result.status=='INCOMPATIBLE'
    assert 'RAM_GENERATION_MISMATCH' in {i.code for i in result.issues}


def test_case_form_factor_or_gpu_clearance_conflict_is_incompatible():
    case=evaluate_compatibility(selection(),catalog(case_factors=('Mini-ITX',)))
    gpu=evaluate_compatibility(selection(),catalog(case_gpu=150))
    assert case.status=='INCOMPATIBLE' and gpu.status=='INCOMPATIBLE'
    assert 'BOARD_CASE_FORM_FACTOR_MISMATCH' in {i.code for i in case.issues}
    assert 'GPU_CLEARANCE_INSUFFICIENT' in {i.code for i in gpu.issues}


def test_unknown_owned_gpu_dimensions_are_unverified():
    selected=selection()
    parts={k:v for k,v in selected.part_ids.items() if k!='gpu'}
    selected=BuildSelection(part_ids=parts,owned_components=(OwnedComponent(kind='gpu',product_id=None,label='My old RTX'),))
    result=evaluate_compatibility(selected,catalog())
    assert result.status=='UNVERIFIED'
    assert 'GPU_CLEARANCE_UNKNOWN' in {i.code for i in result.issues}


def test_missing_psu_connector_is_unverified_not_pass():
    result=evaluate_compatibility(selection(),catalog(omit=('supply.connectors',)))
    assert result.status=='UNVERIFIED'
    assert 'GPU_POWER_CONNECTORS_UNKNOWN' in {i.code for i in result.issues}


def test_valid_fixture_build_is_compatible():
    result=evaluate_compatibility(selection(),catalog())
    assert result.status=='COMPATIBLE'
    assert not result.issues


def test_known_incompatible_overrides_unknown():
    result=evaluate_compatibility(selection(),catalog(board_socket='LGA1700',omit=('supply.connectors',)))
    assert result.status=='INCOMPATIBLE'
    assert {'CPU_SOCKET_MISMATCH','GPU_POWER_CONNECTORS_UNKNOWN'} <= {i.code for i in result.issues}


def test_insufficient_power_is_incompatible():
    result=evaluate_compatibility(selection(),catalog(psu_watts=200))
    assert result.status=='INCOMPATIBLE'
    assert 'PSU_CAPACITY_INSUFFICIENT' in {i.code for i in result.issues}


def test_unknown_case_size_is_not_assumed_compatible():
    result=evaluate_compatibility(selection(),catalog(omit=('chassis.max_gpu_length_mm',)))
    assert result.status=='UNVERIFIED'
    assert 'GPU_CLEARANCE_UNKNOWN' in {i.code for i in result.issues}


def test_duplicate_required_gpu_connectors_need_duplicate_psu_connectors():
    result=evaluate_compatibility(selection(),catalog(gpu_connectors=('8-pin','8-pin'),psu_connectors=('8-pin',)))
    assert result.status=='INCOMPATIBLE'
    assert 'GPU_POWER_CONNECTOR_MISMATCH' in {i.code for i in result.issues}


def test_unrecognized_storage_interface_is_unverified():
    data=catalog()
    products=tuple(p.model_copy(update={'specs':{'interface':'U.2 NVMe'}}) if p.kind=='storage' else p for p in data.products)
    result=evaluate_compatibility(selection(),data.model_copy(update={'products':products}))
    assert result.status=='UNVERIFIED'
    assert 'STORAGE_SUPPORT_UNKNOWN' in {i.code for i in result.issues}
