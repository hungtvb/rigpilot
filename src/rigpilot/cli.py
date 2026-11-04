"""Local diagnostic CLI for catalog imports and non-LLM build recommendations."""
import argparse
import json
import sys
from pathlib import Path

from rigpilot.application.recommend import recommend_from_db
from rigpilot.catalog.store import import_catalog, load_catalog
from rigpilot.domain.models import BuildRequest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rigpilot")
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("import", help="Validate and import curated catalog snapshot")
    ingest.add_argument("--source", type=Path, required=True)
    ingest.add_argument("--db", type=Path, required=True)
    recommend = commands.add_parser("recommend", help="Assess one non-LLM PC build")
    recommend.add_argument("--db", type=Path, required=True)
    recommend.add_argument("--budget-vnd", type=int, required=True)
    recommend.add_argument("--workload", type=str, required=True)
    recommend.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "recommend" and args.budget_vnd < 0:
        parser.error("budget-vnd cannot be negative")
    try:
        if args.command == "import":
            sid = import_catalog(args.source, args.db)
            print(json.dumps({"snapshot_id": sid}))
        else:
            request = BuildRequest(budget_vnd=args.budget_vnd, primary_workload=args.workload)
            result = recommend_from_db(request, args.db)
            payload = {"snapshot_id": load_catalog(args.db).snapshot_id, **result.model_dump(mode="json")}
            if args.json:
                print(json.dumps(payload, indent=2))
            else:
                print(f"{result.status}: " + "; ".join(result.explanation))
        return 0
    except (OSError, ValueError) as error:
        print(f"rigpilot: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
