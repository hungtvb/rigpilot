import json
import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from rigpilot.catalog.store import import_catalog, load_catalog

FIXTURE = Path(__file__).parent / "fixtures" / "catalog_test.json"


def source_copy(tmp_path, change=None):
    p = tmp_path / "source.json"
    doc = json.loads(FIXTURE.read_text())
    if change:
        change(doc)
    p.write_text(json.dumps(doc))
    return p


def test_import_roundtrip_preserves_price_stock_and_model_id(tmp_path):
    db = tmp_path / "store.db"
    h = import_catalog(FIXTURE, db)
    snapshot = load_catalog(db)
    assert snapshot.snapshot_id == h
    assert snapshot.products[0].product_id == "CPU-A"
    assert snapshot.products[0].specs["socket"] == "AM5"
    assert snapshot.offers["CPU-A"].price_vnd == 3500000
    assert snapshot.offers["MB-A"].stock == "UNKNOWN"


def test_import_rejects_duplicate_product_ids_atomically(tmp_path):
    db = tmp_path / "store.db"
    original = import_catalog(FIXTURE, db)
    src = source_copy(tmp_path, lambda x: x["products"].append(x["products"][0]))
    with pytest.raises((ValueError, ValidationError)):
        import_catalog(src, db)
    with sqlite3.connect(db) as connection:
        assert connection.execute("select count(*) from catalog_snapshots").fetchone()[0] == 1
    assert load_catalog(db).snapshot_id == original


def test_import_rejects_negative_spec_values(tmp_path):
    db = tmp_path / "store.db"
    src = source_copy(tmp_path, lambda x: x["products"][0]["specs"].update(tdp_w=-1))
    with pytest.raises((ValueError, ValidationError)):
        import_catalog(src, db)
    if db.exists():
        with sqlite3.connect(db) as connection:
            names = {x[0] for x in connection.execute("select name from sqlite_master where type='table'")}
            if "catalog_snapshots" in names:
                assert connection.execute("select count(*) from catalog_snapshots").fetchone()[0] == 0


def test_missing_price_preserves_none(tmp_path):
    db = tmp_path / "store.db"
    import_catalog(FIXTURE, db)
    assert load_catalog(db).offers["MB-A"].price_vnd is None


def test_same_input_is_idempotent(tmp_path):
    db = tmp_path / "store.db"
    first = import_catalog(FIXTURE, db)
    second = import_catalog(FIXTURE, db)
    assert first == second
    with sqlite3.connect(db) as connection:
        assert connection.execute("select count(*) from catalog_snapshots").fetchone()[0] == 1
