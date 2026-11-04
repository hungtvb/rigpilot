"""Atomic import and snapshot lookups for the local PC catalog."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from .models import CatalogItem, CatalogOffer, CatalogSnapshot

_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS catalog_snapshots (
    snapshot_id TEXT PRIMARY KEY, imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS products (
    snapshot_id TEXT NOT NULL, product_id TEXT NOT NULL, payload TEXT NOT NULL,
    PRIMARY KEY(snapshot_id, product_id),
    FOREIGN KEY(snapshot_id) REFERENCES catalog_snapshots(snapshot_id)
);
CREATE TABLE IF NOT EXISTS offers (
    snapshot_id TEXT NOT NULL, product_id TEXT NOT NULL, payload TEXT NOT NULL,
    PRIMARY KEY(snapshot_id, product_id),
    FOREIGN KEY(snapshot_id, product_id) REFERENCES products(snapshot_id, product_id)
);
"""

def _validate_source(source: dict) -> tuple[list[CatalogItem], list[CatalogOffer], str]:
    if not isinstance(source, dict) or set(source) != {'products', 'offers'}:
        raise ValueError('catalog must contain only products and offers')
    if not isinstance(source['products'], list) or not isinstance(source['offers'], list):
        raise ValueError('products and offers must be lists')
    products = [CatalogItem.model_validate(p) for p in source['products']]
    offers = [CatalogOffer.model_validate(o) for o in source['offers']]
    ids = [p.product_id for p in products]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate product_id in products')
    offer_ids = [o.product_id for o in offers]
    if len(offer_ids) != len(set(offer_ids)):
        raise ValueError('duplicate product_id in offers')
    if set(offer_ids) != set(ids):
        missing = set(offer_ids) - set(ids)
        if missing:
            raise ValueError(f'offer references unknown product: {sorted(missing)}')
        raise ValueError('every product needs a matching offer record, even if price/stock unknown')
    canonical = {
        'products': [p.model_dump(mode='json') for p in sorted(products, key=lambda x: x.product_id)],
        'offers': [o.model_dump(mode='json') for o in sorted(offers, key=lambda x: x.product_id)],
    }
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()
    return products, offers, digest


def import_catalog(source_path: Path, db_path: Path) -> str:
    """Validate complete input first; then commit all records in one SQLite transaction."""
    data = json.loads(Path(source_path).read_text(encoding='utf-8'))
    products, offers, snapshot_id = _validate_source(data)
    with sqlite3.connect(db_path) as conn:
        conn.execute('PRAGMA foreign_keys=ON')
        conn.executescript(_SCHEMA)
        with conn:
            if conn.execute('SELECT 1 FROM catalog_snapshots WHERE snapshot_id=?', (snapshot_id,)).fetchone():
                return snapshot_id
            conn.execute('INSERT INTO catalog_snapshots(snapshot_id) VALUES(?)', (snapshot_id,))
            conn.executemany('INSERT INTO products(snapshot_id,product_id,payload) VALUES(?,?,?)', [
                (snapshot_id, p.product_id, p.model_dump_json()) for p in products
            ])
            conn.executemany('INSERT INTO offers(snapshot_id,product_id,payload) VALUES(?,?,?)', [
                (snapshot_id, o.product_id, o.model_dump_json()) for o in offers
            ])
    return snapshot_id


def load_catalog(db_path: Path, snapshot_id: str | None = None) -> CatalogSnapshot:
    with sqlite3.connect(db_path) as conn:
        conn.execute('PRAGMA foreign_keys=ON')
        if snapshot_id is None:
            row = conn.execute('SELECT snapshot_id FROM catalog_snapshots ORDER BY imported_at DESC, rowid DESC LIMIT 1').fetchone()
            if row is None:
                raise LookupError('no catalog snapshots')
            snapshot_id = row[0]
        elif not conn.execute('SELECT 1 FROM catalog_snapshots WHERE snapshot_id=?', (snapshot_id,)).fetchone():
            raise LookupError(f'unknown catalog snapshot: {snapshot_id}')
        products = tuple(CatalogItem.model_validate_json(row[0]) for row in conn.execute(
            'SELECT payload FROM products WHERE snapshot_id=? ORDER BY product_id', (snapshot_id,)
        ))
        offers = [CatalogOffer.model_validate_json(row[0]) for row in conn.execute(
            'SELECT payload FROM offers WHERE snapshot_id=? ORDER BY product_id', (snapshot_id,)
        )]
    return CatalogSnapshot(snapshot_id=snapshot_id, products=products, offers={o.product_id: o for o in offers})
