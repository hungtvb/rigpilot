"""Shared, typed recommendation domain contracts (no LLM dependence)."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from rigpilot.catalog.models import ComponentKind

CompatibilityStatus = Literal['COMPATIBLE', 'UNVERIFIED', 'INCOMPATIBLE']
IssueSeverity = Literal['ERROR', 'WARNING']


class OwnedComponent(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    kind: ComponentKind
    product_id: str | None = None
    label: str | None = None


class BuildSelection(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    part_ids: dict[ComponentKind, str]
    owned_components: tuple[OwnedComponent, ...] = ()

    @model_validator(mode='after')
    def no_duplicate_component_kinds(self) -> 'BuildSelection':
        owned = [part.kind for part in self.owned_components]
        if len(owned) != len(set(owned)) or set(owned) & set(self.part_ids):
            raise ValueError('owned and purchased parts must not duplicate component kinds')
        return self


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    code: str
    severity: IssueSeverity
    affected_part_ids: tuple[str, ...] = ()
    message: str


class CompatibilityReport(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    status: CompatibilityStatus
    issues: tuple[ValidationIssue, ...] = ()


class BuildRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    budget_vnd: int = Field(ge=0)
    primary_workload: str = Field(min_length=1)
    secondary_workloads: tuple[str, ...] = ()
    locked_parts: dict[ComponentKind, str] = Field(default_factory=dict)
    owned_components: tuple[OwnedComponent, ...] = ()
    previous_parts: dict[ComponentKind, str] | None = None
    approved_replacements: tuple[tuple[str, str], ...] = ()


class ConstraintReport(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    total_purchase_vnd: int | None
    budget_verified: bool
    stock_status: Literal['IN_STOCK', 'OUT_OF_STOCK', 'UNKNOWN']
    approval_required: bool
    issues: tuple[ValidationIssue, ...] = ()


class RecommendationResult(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    status: Literal['RECOMMENDED', 'PROVISIONAL', 'APPROVAL_REQUIRED', 'NO_CANDIDATE']
    selected: BuildSelection | None = None
    compatibility: CompatibilityReport | None = None
    constraints: ConstraintReport | None = None
    evidence_ids: tuple[str, ...] = ()
    selection_limited: bool = False
    explanation: tuple[str, ...] = ()
