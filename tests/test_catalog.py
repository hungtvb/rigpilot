import json
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest

from rigpilot.catalog.store import import_catalog, load_catalog


FIXTURE = Path(__file__).parent / 'fixtures' / 'catalog_test.json'


def fixture_data():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def write_data(tmp_path, data):
    source = tmp_path / 'source.json'
    source.write_text(json.dumps(data), encoding='utf-8')
    return source


def test_import_roundtrip_preserves_price_stock_and_model_id(tmp_path):
    db = tmp_path / 'catalog.db'
    snapshot_id = import_catalog(FIXTURE, db)
    snapshot = load_catalog(db, snapshot_id)
    assert snapshot.snapshot_id == snapshot_id
    assert {p.product_id for p in snapshot.products} == {'cpu-demo', 'gpu-demo'}
    assert snapshot.offers['gpu-demo'].stock == 'OUT_OF_STOCK'
    assert snapshot.offers['cpu-demo'].price_vnd == 3500000
    assert next(p for p in snapshot.products if p.product_id == 'cpu-demo').model == 'Test CPU A'
    assert load_catalog(db) == snapshot


def test_import_rejects_duplicate_product_ids_atomically(tmp_path):
    db = tmp_path / 'catalog.db'
    snapshot_id = import_catalog(FIXTURE, db)
    data = fixture_data()
    data['products'].append(deepcopy(data['products'][0]))
    with pytest.raises(ValueError, match='duplicate product_id'):
        import_catalog(write_data(tmp_path, data), db)
    assert load_catalog(db).snapshot_id == snapshot_id
    with sqlite3.connect(db) as con:
        assert con.execute('SELECT COUNT(*) FROM products').fetchone()[0] == 2


def test_import_rejects_negative_spec_values(tmp_path):
    db = tmp_path / 'catalog.db'
    data = fixture_data()
    data['products'][0]['specs']['tdp_w'] = -25
    with pytest.raises(ValueError, match='tdp_w'):
        import_catalog(write_data(tmp_path, data), db)
    if db.exists():
        with sqlite3.connect(db) as con:
            assert con.execute("SELECT name FROM sqlite_master WHERE name='catalog_snapshots'").fetchone() is None or con.execute('SELECT COUNT(*) FROM catalog_snapshots').fetchone()[0] == 0


def test_missing_price_preserves_none(tmp_path):
    db = tmp_path / 'catalog.db'
    data = fixture_data()
    data['offers'][1]['price_vnd'] = None
    import_catalog(write_data(tmp_path, data), db)
    assert load_catalog(db).offers['gpu-demo'].price_vnd is None


def test_same_input_is_idempotent(tmp_path):
    db = tmp_path / 'catalog.db'
    snapshot_id = import_catalog(FIXTURE, db)
    assert import_catalog(FIXTURE, db) == snapshot_id
    with sqlite3.connect(db) as con:
        assert con.execute('SELECT COUNT(*) FROM catalog_snapshots').fetchone()[0] == 1
        assert con.execute('SELECT COUNT(*) FROM products').fetchone()[0] == 2
        assert con.execute('SELECT COUNT(*) FROM offers').fetchone()[0] == 2


def test_rejects_offer_for_unknown_product_without_altering_current_snapshot(tmp_path):
    db = tmp_path / 'catalog.db'
    before = import_catalog(FIXTURE, db)
    data = fixture_data()
    data['offers'].append({'product_id':'ghost', 'price_vnd':100, 'stock':'IN_STOCK','snapshot_at':'2026-11-04'})
    with pytest.raises(ValueError, match='unknown product'):
        import_catalog(write_data(tmp_path, data), db)
    assert load_catalog(db).snapshot_id == before


def test_invalid_stock_or_price_is_not_coerced(tmp_path):
    data = fixture_data()
    data['offers'][0]['stock'] = 'AVAILABLE'
    with pytest.raises(ValueError):
        import_catalog(write_data(tmp_path,data),tmp_path/'db')
    data = fixture_data()
    data['offers'][0]['price_vnd'] = -1
    with pytest.raises(ValueError):
        import_catalog(write_data(tmp_path,data),tmp_path/'db')
