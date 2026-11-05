"""Local deterministic catalog import and recommendation CLI.

This is not a chat agent and does not make OpenAI requests.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from pydantic import ValidationError

from rigpilot.application.recommend import recommend_from_db
from rigpilot.catalog.store import import_catalog, load_catalog
from rigpilot.domain.models import BuildRequest


def nonnegative_vnd(value: str) -> int:
    try:
        amount=int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('budget-vnd must be an integer') from exc
    if amount<0:
        raise argparse.ArgumentTypeError('budget-vnd cannot be negative')
    return amount


def parser() -> argparse.ArgumentParser:
    p=argparse.ArgumentParser(description='RigPilot deterministic local core (no LLM)')
    sub=p.add_subparsers(dest='command',required=True)
    imp=sub.add_parser('import',help='Import a validated versioned local catalog')
    imp.add_argument('--source',type=Path,required=True)
    imp.add_argument('--db',type=Path,required=True)
    reco=sub.add_parser('recommend',help='Evaluate a non-LLM PC configuration')
    reco.add_argument('--db',type=Path,required=True)
    reco.add_argument('--budget-vnd',type=nonnegative_vnd,required=True)
    reco.add_argument('--workload',required=True)
    reco.add_argument('--json',action='store_true')
    return p


def main(argv: list[str] | None = None) -> int:
    p=parser()
    args=p.parse_args(argv)
    try:
        if args.command=='import':
            snapshot_id=import_catalog(args.source,args.db)
            print(json.dumps({'snapshot_id':snapshot_id,'status':'IMPORTED'}))
            return 0
        request=BuildRequest(budget_vnd=args.budget_vnd,primary_workload=args.workload)
        snapshot=load_catalog(args.db)
        result=recommend_from_db(request,args.db,snapshot.snapshot_id)
        output={'snapshot_id':snapshot.snapshot_id,**result.model_dump(mode='json')}
        if args.json:
            print(json.dumps(output,ensure_ascii=False))
        else:
            print(f'Status: {result.status}; snapshot: {snapshot.snapshot_id}')
            for line in result.explanation:
                print(line)
        return 0
    except sqlite3.DatabaseError as exc:
        print(f'Catalog database error: {exc}', file=sys.stderr)
        return 1
    except (OSError, ValueError, LookupError, ValidationError) as exc:
        print(f'{type(exc).__name__}: {exc}',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
