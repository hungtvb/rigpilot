"""Authoritative imported product and synthetic shop-offer contracts."""
from __future__ import annotations

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

ComponentKind = Literal['cpu', 'motherboard', 'ram', 'gpu', 'storage', 'psu', 'case', 'cooler']
StockState = Literal['IN_STOCK', 'OUT_OF_STOCK', 'UNKNOWN']
SpecValue = str | int | bool | list[str]

_NONNEGATIVE_NUMERIC = {
    'tdp_w', 'length_mm', 'board_power_w', 'rated_w', 'max_gpu_length_mm',
    'height_mm', 'max_cooler_height_mm', 'm2_slots', 'capacity_gb',
}
_LIST_SPEC = {'connectors', 'power_connectors', 'supported_form_factors', 'supported_sockets', 'supported_memory_types'}
_STRING_SPEC = {'socket', 'memory_type', 'form_factor', 'interface'}

class CatalogItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    product_id: str = Field(min_length=1)
    kind: ComponentKind
    brand: str = Field(min_length=1)
    model: str = Field(min_length=1)
    specs: dict[str, SpecValue]
    spec_source_url: str | None = None
    spec_checked_at: str | None = None
    workload_fit_tier: dict[str, Annotated[int, Field(ge=0, le=3)]] = Field(default_factory=dict)
    fit_evidence_ids: dict[str, list[str]] = Field(default_factory=dict)

    @model_validator(mode='after')
    def validate_specs(self) -> 'CatalogItem':
        for name, value in self.specs.items():
            if name in _NONNEGATIVE_NUMERIC and (type(value) is not int or value < 0):
                raise ValueError(f'{name} must be a nonnegative integer')
            if name in _LIST_SPEC and (not isinstance(value, list) or not all(isinstance(x, str) and x.strip() for x in value)):
                raise ValueError(f'{name} must be a list of names')
            if name in _STRING_SPEC and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f'{name} must be a nonempty string')
            if type(value) not in (str, int, bool, list):
                raise ValueError(f'unsupported spec type for {name}')
            if isinstance(value, list) and not all(isinstance(x, str) for x in value):
                raise ValueError(f'{name} list items must be strings')
        if self.spec_source_url is not None:
            parsed = HttpUrl(self.spec_source_url)
            if parsed.scheme != 'https':
                raise ValueError('spec_source_url must use HTTPS')
        return self

class CatalogOffer(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    product_id: str = Field(min_length=1)
    price_vnd: int | None = Field(default=None, ge=0)
    stock: StockState
    snapshot_at: str = Field(min_length=1)

class CatalogSnapshot(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    snapshot_id: str
    products: tuple[CatalogItem, ...]
    offers: dict[str, CatalogOffer]
