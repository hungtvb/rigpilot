"""Conservative, deterministic compatibility checks; unknown is never PASS."""
from __future__ import annotations

from collections import Counter

from rigpilot.catalog.models import CatalogItem, CatalogSnapshot
from .models import BuildSelection, CompatibilityReport, ValidationIssue, REQUIRED_COMPONENT_KINDS


# Generic PSU "8-pin" can refer to CPU EPS or GPU PCIe; never infer the cable.
_GPU_POWER_CONNECTOR_TYPES = {
    '8-pin': 'PCIe-8-pin', 'PCIe-8-pin': 'PCIe-8-pin',
    '6-pin': 'PCIe-6-pin', 'PCIe-6-pin': 'PCIe-6-pin',
    '12V-2x6': '12V-2x6',
}
_PSU_CONNECTOR_TYPES = {
    'PCIe-8-pin': 'PCIe-8-pin', 'PCIe-6+2-pin': 'PCIe-8-pin',
    'PCIe-6-pin': 'PCIe-6-pin', '12V-2x6': '12V-2x6',
    'EPS-8-pin': None, 'ATX-24-pin': None,
}


class PowerPolicy:
    """Conservative indicative headroom, not electrical certification."""
    BASE_SYSTEM_OVERHEAD_W = 150
    HEADROOM_MULTIPLIER = 1.20


def evaluate_compatibility(build: BuildSelection, snapshot: CatalogSnapshot) -> CompatibilityReport:
    lookup = {part.product_id: part for part in snapshot.products}
    selected: dict[str, CatalogItem | None] = {}
    issues: list[ValidationIssue] = []

    def issue(code: str, reason: str, *parts: str, unknown: bool = False) -> None:
        issues.append(ValidationIssue(code=code, severity='WARNING' if unknown else 'ERROR', affected_part_ids=tuple(parts), message=reason))

    for kind, pid in build.part_ids.items():
        product = lookup.get(pid)
        if product is None or product.kind != kind:
            issue('INVALID_SELECTED_PART', f'Unknown or wrong-kind {kind}: {pid}', pid)
        selected[kind] = product if product and product.kind == kind else None
    for owned in build.owned_components:
        part = lookup.get(owned.product_id) if owned.product_id else None
        selected[owned.kind] = part if part and part.kind == owned.kind else None
        if part is None:
            issue('OWNED_PART_UNVERIFIED', f'Owned {owned.kind} model/specification is not verified', owned.label or owned.product_id or owned.kind, unknown=True)

    present_kinds = set(build.part_ids) | {owned.kind for owned in build.owned_components}
    for required_kind in REQUIRED_COMPONENT_KINDS:
        if required_kind not in present_kinds:
            issue('MISSING_REQUIRED_COMPONENT',
                  f'No {required_kind} component was selected or supplied as owned',
                  required_kind, unknown=True)

    def spec(kind: str, name: str):
        product = selected.get(kind)
        return None if product is None else product.specs.get(name)

    def match(left_kind: str, left_key: str, right_kind: str, right_key: str, code: str, unknown_code: str):
        left, right = spec(left_kind, left_key), spec(right_kind, right_key)
        if left is None or right is None:
            issue(unknown_code, f'Cannot verify {left_kind} {left_key} against {right_kind} {right_key}', left_kind, right_kind, unknown=True)
        elif left != right:
            issue(code, f'{left_kind} {left_key} {left!r} does not match {right_kind} {right_key} {right!r}', left_kind, right_kind)

    match('cpu', 'socket', 'motherboard', 'socket', 'CPU_SOCKET_MISMATCH', 'CPU_SOCKET_UNKNOWN')
    match('ram', 'memory_type', 'motherboard', 'memory_type', 'RAM_GENERATION_MISMATCH', 'RAM_GENERATION_UNKNOWN')
    cpu_types = spec('cpu', 'supported_memory_types')
    board_type = spec('motherboard', 'memory_type')
    if cpu_types is not None:
        if board_type is None:
            issue('CPU_MEMORY_GENERATION_UNKNOWN', 'Motherboard memory generation is unknown', 'cpu', 'motherboard', unknown=True)
        elif board_type not in cpu_types:
            issue('CPU_MEMORY_GENERATION_MISMATCH', f'CPU does not support {board_type}', 'cpu', 'motherboard')
    else:
        match('cpu', 'memory_type', 'motherboard', 'memory_type', 'CPU_MEMORY_GENERATION_MISMATCH', 'CPU_MEMORY_GENERATION_UNKNOWN')

    mobo_form, case_forms = spec('motherboard', 'form_factor'), spec('case', 'supported_form_factors')
    if mobo_form is None or case_forms is None:
        issue('BOARD_CASE_FORM_FACTOR_UNKNOWN', 'Missing case or board form factor', 'motherboard', 'case', unknown=True)
    elif mobo_form not in case_forms:
        issue('BOARD_CASE_FORM_FACTOR_MISMATCH', 'Motherboard does not fit the selected case', 'motherboard', 'case')

    gpu = selected.get('gpu')
    if 'gpu' in selected:
        gpu_len, case_gpu = spec('gpu','length_mm'), spec('case','max_gpu_length_mm')
        if gpu_len is None or case_gpu is None:
            issue('GPU_CLEARANCE_UNKNOWN', 'GPU/case length clearance cannot be verified', 'gpu','case',unknown=True)
        elif gpu_len > case_gpu:
            issue('GPU_CLEARANCE_INSUFFICIENT', 'GPU length exceeds case clearance', 'gpu','case')
        gpu_conn, psu_conn = spec('gpu','power_connectors'), spec('psu','connectors')
        if gpu_conn is None or psu_conn is None:
            issue('GPU_POWER_CONNECTORS_UNKNOWN', 'GPU power connector availability is unverified', 'gpu','psu',unknown=True)
        else:
            required = [_GPU_POWER_CONNECTOR_TYPES.get(name) for name in gpu_conn]
            if any(name is None for name in required):
                issue('GPU_POWER_CONNECTORS_UNKNOWN', 'GPU connector type is not recognized', 'gpu', unknown=True)
            else:
                available = [
                    _PSU_CONNECTOR_TYPES[name]
                    for name in psu_conn
                    if name in _PSU_CONNECTOR_TYPES and _PSU_CONNECTOR_TYPES[name] is not None
                ]
                need = Counter(required)
                have = Counter(available)
                if any(have[connector] < count for connector, count in need.items()):
                    if any(name not in _PSU_CONNECTOR_TYPES for name in psu_conn):
                        issue('GPU_POWER_CONNECTORS_UNKNOWN',
                              'PSU connector labels are ambiguous; cannot verify dedicated GPU PCIe cables',
                              'gpu', 'psu', unknown=True)
                    else:
                        issue('GPU_POWER_CONNECTOR_MISMATCH',
                              'PSU lacks sufficient dedicated GPU PCIe power connectors',
                              'gpu', 'psu')

    if 'cooler' in selected:
        supported, socket = spec('cooler','supported_sockets'), spec('cpu','socket')
        if supported is None or socket is None:
            issue('COOLER_SOCKET_UNKNOWN','Cannot verify cooler socket support','cooler','cpu',unknown=True)
        elif socket not in supported:
            issue('COOLER_SOCKET_MISMATCH','Cooler does not support CPU socket','cooler','cpu')
        cooler_height, case_max = spec('cooler','height_mm'),spec('case','max_cooler_height_mm')
        if cooler_height is None or case_max is None:
            issue('COOLER_CLEARANCE_UNKNOWN','Cannot verify cooler height','cooler','case',unknown=True)
        elif cooler_height > case_max:
            issue('COOLER_CLEARANCE_INSUFFICIENT','Cooler exceeds case height allowance','cooler','case')

    if 'storage' in selected:
        interface,slots = spec('storage','interface'),spec('motherboard','m2_slots')
        if isinstance(interface,str) and interface.startswith('M.2 NVMe'):
            if slots is None:
                issue('STORAGE_SUPPORT_UNKNOWN','Motherboard M.2 slot count is unknown','storage','motherboard',unknown=True)
            elif slots <= 0:
                issue('STORAGE_SUPPORT_MISMATCH','Selected motherboard has no M.2 slot','storage','motherboard')
        else:
            issue('STORAGE_SUPPORT_UNKNOWN','Unverified storage interface or motherboard support','storage','motherboard',unknown=True)

    if 'gpu' in selected:
        cpu_w,gpu_w,psu_w = spec('cpu','tdp_w'),spec('gpu','board_power_w'),spec('psu','rated_w')
        if cpu_w is None or gpu_w is None or psu_w is None:
            issue('PSU_CAPACITY_UNKNOWN','Cannot verify CPU/GPU/PSU power estimate','cpu','gpu','psu',unknown=True)
        elif psu_w < (cpu_w + gpu_w + PowerPolicy.BASE_SYSTEM_OVERHEAD_W) * PowerPolicy.HEADROOM_MULTIPLIER:
            issue('PSU_CAPACITY_INSUFFICIENT','PSU rated wattage is below conservative headroom estimate','psu')

    if any(x.severity == 'ERROR' for x in issues):
        status = 'INCOMPATIBLE'
    elif issues:
        status = 'UNVERIFIED'
    else:
        status = 'COMPATIBLE'
    return CompatibilityReport(status=status, issues=tuple(issues))
