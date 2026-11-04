"""Conservative, deterministic PC hardware compatibility assessments.

Missing evidence always produces UNVERIFIED. PSU power is policy-based,
not a certification that a particular real-world build will run safely.
"""
from dataclasses import dataclass
from math import ceil

from rigpilot.catalog.models import CatalogItem, CatalogSnapshot
from rigpilot.domain.models import BuildSelection, CompatibilityReport, ValidationIssue


@dataclass(frozen=True)
class PowerPolicy:
    system_overhead_w: int = 150
    safety_multiplier: float = 1.2

    def required_watts(self, cpu_tdp_w: int, gpu_board_power_w: int) -> int:
        return ceil((cpu_tdp_w + gpu_board_power_w + self.system_overhead_w) * self.safety_multiplier)


def evaluate_compatibility(build: BuildSelection, snapshot: CatalogSnapshot) -> CompatibilityReport:
    by_id = {p.product_id: p for p in snapshot.products}
    selected: dict[str, CatalogItem] = {}
    issues: list[ValidationIssue] = []

    def add(code: str, severity: str, message: str, *ids: str):
        issues.append(ValidationIssue(code=code, severity=severity, message=message, affected_part_ids=tuple(x for x in ids if x)))

    for kind, pid in build.part_ids.items():
        part = by_id.get(pid)
        if part is None:
            add("PRODUCT_NOT_FOUND", "UNVERIFIED", f"Unresolved catalog product: {pid}", pid)
        elif part.kind != kind:
            add("PRODUCT_KIND_MISMATCH", "INCOMPATIBLE", f"{pid} is not a {kind}", pid)
        else:
            selected[kind] = part
    for owned in build.owned_components:
        if owned.product_id is None:
            add("OWNED_MODEL_UNKNOWN", "UNVERIFIED", f"Unknown model for owned {owned.kind}")
        else:
            match = by_id.get(owned.product_id)
            if match is None or match.kind != owned.kind:
                add("OWNED_MODEL_UNVERIFIED", "UNVERIFIED", f"Cannot verify owned {owned.kind}", owned.product_id)
            else:
                selected[owned.kind] = match

    for kind in ("cpu", "motherboard", "ram", "gpu", "storage", "psu", "case", "cooler"):
        if kind not in selected and all(o.kind != kind for o in build.owned_components):
            add("MISSING_COMPONENT", "UNVERIFIED", f"No {kind} selected")

    def field(kind: str, key: str):
        part = selected.get(kind)
        return part.specs.get(key) if part else None

    def equal(k1: str, v1: str, k2: str, v2: str, error: str, unknown: str):
        a, b = field(k1, v1), field(k2, v2)
        if a is None or b is None:
            add(unknown, "UNVERIFIED", f"Cannot verify {k1}.{v1} against {k2}.{v2}")
        elif a != b:
            add(error, "INCOMPATIBLE", f"{k1}.{v1}={a} conflicts with {k2}.{v2}={b}", *(p.product_id for p in (selected[k1], selected[k2])))

    equal("cpu", "socket", "motherboard", "socket", "CPU_SOCKET_MISMATCH", "CPU_SOCKET_UNKNOWN")
    equal("ram", "memory_type", "motherboard", "memory_type", "RAM_GENERATION_MISMATCH", "RAM_GENERATION_UNKNOWN")
    equal("cpu", "memory_type", "ram", "memory_type", "CPU_MEMORY_MISMATCH", "CPU_MEMORY_UNKNOWN")

    form, supported = field("motherboard", "form_factor"), field("case", "supported_form_factors")
    if form is None or supported is None:
        add("CASE_FORM_FACTOR_UNKNOWN", "UNVERIFIED", "Case/motherboard form factor unknown")
    elif form not in supported:
        add("CASE_FORM_FACTOR_MISMATCH", "INCOMPATIBLE", "Motherboard does not fit case")

    for part, dim, maxdim, bad, unknown in (
        ("gpu", "length_mm", "max_gpu_length_mm", "GPU_CLEARANCE_FAIL", "GPU_CLEARANCE_UNKNOWN"),
        ("cooler", "height_mm", "max_cooler_height_mm", "COOLER_CLEARANCE_FAIL", "COOLER_CLEARANCE_UNKNOWN"),
    ):
        size, clearance = field(part, dim), field("case", maxdim)
        if size is None or clearance is None:
            add(unknown, "UNVERIFIED", f"{part} dimension/case clearance unknown")
        elif size > clearance:
            add(bad, "INCOMPATIBLE", f"{part} exceeds case clearance")

    sockets, cpu_socket = field("cooler", "supported_sockets"), field("cpu", "socket")
    if sockets is None or cpu_socket is None:
        add("COOLER_SOCKET_UNKNOWN", "UNVERIFIED", "Cannot confirm cooler mount support")
    elif cpu_socket not in sockets:
        add("COOLER_SOCKET_MISMATCH", "INCOMPATIBLE", "Cooler does not support CPU socket")

    storage_intf, m2_slots = field("storage", "interface"), field("motherboard", "m2_slots")
    if storage_intf is None:
        add("STORAGE_INTERFACE_UNKNOWN", "UNVERIFIED", "Storage interface unknown")
    elif storage_intf == "M.2_NVMe":
        if m2_slots is None:
            add("STORAGE_SLOT_UNVERIFIED", "UNVERIFIED", "Motherboard M.2 support unknown")
        elif m2_slots < 1:
            add("STORAGE_SLOT_MISSING", "INCOMPATIBLE", "Motherboard lacks M.2 slot")
    else:
        add("STORAGE_INTERFACE_UNVERIFIED", "UNVERIFIED", "No reviewed rule for storage interface")

    gpu_connectors, psu_connectors = field("gpu", "power_connectors"), field("psu", "connectors")
    if gpu_connectors is None or psu_connectors is None:
        add("PSU_CONNECTOR_UNVERIFIED", "UNVERIFIED", "Required GPU/PSU connectors unknown")
    elif not set(gpu_connectors).issubset(psu_connectors):
        add("PSU_CONNECTOR_MISMATCH", "INCOMPATIBLE", "PSU does not supply required GPU connectors")

    cpu_w, gpu_w, psu_w = field("cpu", "tdp_w"), field("gpu", "board_power_w"), field("psu", "rated_w")
    if any(x is None for x in (cpu_w, gpu_w, psu_w)):
        add("PSU_CAPACITY_UNVERIFIED", "UNVERIFIED", "Missing input for conservative PSU sizing policy")
    elif psu_w < PowerPolicy().required_watts(cpu_w, gpu_w):
        add("PSU_CAPACITY_POLICY_FAIL", "INCOMPATIBLE", "PSU rating is below conservative sizing policy")

    status = "INCOMPATIBLE" if any(x.severity == "INCOMPATIBLE" for x in issues) else (
        "UNVERIFIED" if issues else "COMPATIBLE"
    )
    return CompatibilityReport(status=status, issues=tuple(issues))
