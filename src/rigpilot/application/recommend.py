"""One deterministic application use case; future agent workflows reuse it."""
from pathlib import Path

from rigpilot.catalog.store import load_catalog
from rigpilot.domain.models import BuildRequest, RecommendationResult
from rigpilot.domain.optimizer import optimize_build


def recommend_from_db(
    request: BuildRequest, db_path: Path, snapshot_id: str | None = None
) -> RecommendationResult:
    snapshot = load_catalog(db_path, snapshot_id)
    return optimize_build(request, snapshot)
