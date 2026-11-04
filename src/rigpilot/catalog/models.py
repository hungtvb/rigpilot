"""Validated, source-aware hardware catalog records (shop offers are synthetic)."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ComponentKind = Literal["cpu", "motherboard", "ram", "gpu", "storage", "psu", "case", "cooler"]
StockState = Literal["IN_STOCK", "OUT_OF_STOCK", "UNKNOWN"]
SpecValue = str | int | bool | list[str]

_SPEC_TYPES: dict[str, type] = {
    "socket": str, "memory_type": str, "tdp_w": int, "form_factor": str,
    "m2_slots": int, "length_mm": int, "board_power_w": int,
    "power_connectors": list, "rated_w": int, "connectors": list,
    "supported_form_factors": list, "max_gpu_length_mm": int,
    "max_cooler_height_mm": int, "supported_sockets": list,
    "height_mm": int, "interface": str, "capacity_gb": int,
}
_POSITIVE = {
    "tdp_w", "m2_slots", "length_mm", "board_power_w", "rated_w",
    "max_gpu_length_mm", "max_cooler_height_mm", "height_mm", "capacity_gb",
}


class CatalogItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    product_id: str = Field(min_length=1)
    kind: ComponentKind
    brand: str = Field(min_length=1)
    model: str = Field(min_length=1)
    specs: dict[str, SpecValue]
    spec_source_url: str | None = None
    spec_checked_at: str | None = None
    workload_fit_tier: dict[str, int] = Field(default_factory=dict)
    fit_evidence_ids: dict[str, list[str]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_specs(self) -> "CatalogItem":
        for key, value in self.specs.items():
            expected = _SPEC_TYPES.get(key)
            if expected is None:
                raise ValueError(f"unsupported spec field: {key}")
            if type(value) is not expected:
                raise ValueError(f"{key} must be {expected.__name__}")
            if key in _POSITIVE and value < 0:
                raise ValueError(f"negative {key} forbidden")
            if expected is list and not all(type(x) is str and x for x in value):
                raise ValueError(f"invalid string list: {key}")
        if any(type(v) is not int or not 0 <= v <= 3 for v in self.workload_fit_tier.values()):
            raise ValueError("workload_fit_tier must have qualitative tiers 0..3")
        if self.spec_source_url is not None and not self.spec_source_url.startswith("https://"):
            raise ValueError("source must be a verified https URL")
        return self


class CatalogOffer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    product_id: str = Field(min_length=1)
    price_vnd: int | None = Field(default=None, ge=0, strict=True)
    stock: StockState
    snapshot_at: str = Field(min_length=1)


class CatalogDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    products: list[CatalogItem]
    offers: list[CatalogOffer]

    @model_validator(mode="after")
    def validate_ids(self) -> "CatalogDocument":
        pids = [p.product_id for p in self.products]
        oids = [o.product_id for o in self.offers]
        if len(pids) != len(set(pids)) or len(oids) != len(set(oids)):
            raise ValueError("duplicate product/offer ids")
        if set(oids) != set(pids):
            raise ValueError("every product needs exactly one offer")
        if not pids:
            raise ValueError("cannot import an empty catalog")
        return self


class CatalogSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    snapshot_id: str
    products: tuple[CatalogItem, ...]
    offers: dict[str, CatalogOffer]
