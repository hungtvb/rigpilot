from rigpilot.catalog.models import CatalogItem, CatalogOffer, CatalogSnapshot
from rigpilot.domain.models import BuildSelection, OwnedComponent
from rigpilot.domain.compatibility import evaluate_compatibility


def snapshot(**spec_changes):
    samples = {
        "cpu": {"socket": "AM5", "memory_type": "DDR5", "tdp_w": 65},
        "motherboard": {"socket": "AM5", "memory_type": "DDR5", "form_factor": "Micro-ATX", "m2_slots": 2},
        "ram": {"memory_type": "DDR5"},
        "gpu": {"length_mm": 200, "board_power_w": 120, "power_connectors": ["PCIe_8pin"]},
        "storage": {"interface": "M.2_NVMe"},
        "psu": {"rated_w": 750, "connectors": ["PCIe_8pin"]},
        "case": {"supported_form_factors": ["Micro-ATX"], "max_gpu_length_mm": 300, "max_cooler_height_mm": 170},
        "cooler": {"supported_sockets": ["AM5"], "height_mm": 155},
    }
    for k, changes in spec_changes.items():
        samples[k].update({a:b for a,b in changes.items() if b is not None})
        for a,b in changes.items():
            if b is None: samples[k].pop(a,None)
    items = tuple(CatalogItem(product_id=f"{k}-1",kind=k,brand="Fixture",model=f"{k} 1",specs=specs) for k,specs in samples.items())
    offers={x.product_id:CatalogOffer(product_id=x.product_id,price_vnd=1,stock="IN_STOCK",snapshot_at="2026-11-04") for x in items}
    return CatalogSnapshot(snapshot_id="test",products=items,offers=offers)


def selection(**changes):
    parts={k:f"{k}-1" for k in ("cpu","motherboard","ram","gpu","storage","psu","case","cooler")}
    parts.update(changes)
    return BuildSelection(part_ids=parts)


def codes(report):
    return {x.code for x in report.issues}


def test_socket_conflict_is_incompatible():
    r=evaluate_compatibility(selection(),snapshot(cpu={"socket":"LGA1700"}))
    assert r.status=="INCOMPATIBLE" and "CPU_SOCKET_MISMATCH" in codes(r)


def test_ram_generation_conflict_is_incompatible():
    r=evaluate_compatibility(selection(),snapshot(ram={"memory_type":"DDR4"}))
    assert r.status=="INCOMPATIBLE" and "RAM_GENERATION_MISMATCH" in codes(r)


def test_case_form_factor_or_gpu_clearance_conflict_is_incompatible():
    r=evaluate_compatibility(selection(),snapshot(case={"supported_form_factors":["Mini-ITX"],"max_gpu_length_mm":150}))
    assert r.status=="INCOMPATIBLE"
    assert {"CASE_FORM_FACTOR_MISMATCH","GPU_CLEARANCE_FAIL"} <= codes(r)


def test_unknown_owned_gpu_dimensions_are_unverified():
    s=selection()
    s.part_ids.pop("gpu")
    s=BuildSelection(part_ids=s.part_ids,owned_components=(OwnedComponent(kind="gpu",label="RTX 4070 of unknown brand"),))
    r=evaluate_compatibility(s,snapshot())
    assert r.status=="UNVERIFIED" and "OWNED_MODEL_UNKNOWN" in codes(r)
    assert "GPU_CLEARANCE_UNKNOWN" in codes(r)


def test_missing_psu_connector_is_unverified_not_pass():
    r=evaluate_compatibility(selection(),snapshot(psu={"connectors":None}))
    assert r.status=="UNVERIFIED" and "PSU_CONNECTOR_UNVERIFIED" in codes(r)


def test_valid_fixture_build_is_compatible():
    r=evaluate_compatibility(selection(),snapshot())
    assert r.status=="COMPATIBLE" and not r.issues


def test_known_incompatible_dominates_independent_unknown():
    r=evaluate_compatibility(selection(),snapshot(cpu={"socket":"LGA1700"}, gpu={"length_mm":None}))
    assert r.status=="INCOMPATIBLE"


def test_storage_requires_a_compatible_slot():
    r=evaluate_compatibility(selection(),snapshot(motherboard={"m2_slots":0}))
    assert r.status=="INCOMPATIBLE" and "STORAGE_SLOT_MISSING" in codes(r)
