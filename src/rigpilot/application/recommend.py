"""Application-level catalog lookup and deterministic recommendation entrypoint."""
from pathlib import Path

from rigpilot.catalog.store import load_catalog
from rigpilot.domain.models import BuildRequest, RecommendationResult
from rigpilot.domain.optimizer import optimize_build


def recommend_from_db(request: BuildRequest, db_path: Path, snapshot_id: str | None = None) -> RecommendationResult:
    return optimize_build(request, load_catalog(db_path,snapshot_id))
