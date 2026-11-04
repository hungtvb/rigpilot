"""Domain contracts shared by non-LLM compatibility, constraints and optimization."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from rigpilot.catalog.models import ComponentKind

CompatibilityStatus = Literal["COMPATIBLE", "UNVERIFIED", "INCOMPATIBLE"]
Severity = Literal["UNVERIFIED", "INCOMPATIBLE", "WARNING", "APPROVAL_REQUIRED"]


class OwnedComponent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: ComponentKind
    product_id: str | None = None
    label: str | None = None


class BuildSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    part_ids: dict[ComponentKind, str]
    owned_components: tuple[OwnedComponent, ...] = ()

    @model_validator(mode="after")
    def unique_kinds(self) -> "BuildSelection":
        owned_kinds = [o.kind for o in self.owned_components]
        if len(owned_kinds) != len(set(owned_kinds)):
            raise ValueError("duplicate owned part kind")
        for owned in self.owned_components:
            if owned.kind in self.part_ids and owned.product_id and self.part_ids[owned.kind] != owned.product_id:
                raise ValueError("selected owned product must match owned part")
            if owned.kind in self.part_ids and owned.product_id is None:
                raise ValueError("cannot pretend an unknown owned model has a selected product ID")
        return self


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    code: str
    severity: Severity
    affected_part_ids: tuple[str, ...] = ()
    message: str


class CompatibilityReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    status: CompatibilityStatus
    issues: tuple[ValidationIssue, ...] = ()
