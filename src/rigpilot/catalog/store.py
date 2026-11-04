"""Atomic SQLite catalog import and immutable snapshot loading."""
import hashlib
import json
import sqlite3
from pathlib import Path

from rigpilot.catalog.models import CatalogDocument, CatalogItem, CatalogOffer, CatalogSnapshot


_SCHEMA = """
CREATE TABLE IF NOT EXISTS catalog_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS products (
    snapshot_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, product_id),
    FOREIGN KEY (snapshot_id) REFERENCES catalog_snapshots(snapshot_id)
);
CREATE TABLE IF NOT EXISTS offers (
    snapshot_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, product_id),
    FOREIGN KEY (snapshot_id, product_id) REFERENCES products(snapshot_id, product_id)
);
"""


def _open(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript(_SCHEMA)
    return connection


def import_catalog(source_path: Path, db_path: Path) -> str:
    document = CatalogDocument.model_validate_json(source_path.read_text(encoding="utf-8"))
    canonical = {
        "products": [p.model_dump(mode="json") for p in sorted(document.products, key=lambda x: x.product_id)],
        "offers": [o.model_dump(mode="json") for o in sorted(document.offers, key=lambda x: x.product_id)],
    }
    snapshot_id = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    connection = _open(db_path)
    try:
        with connection:
            connection.execute("INSERT OR IGNORE INTO catalog_snapshots(snapshot_id) VALUES (?)", (snapshot_id,))
            for product in document.products:
                connection.execute(
                    "INSERT OR IGNORE INTO products (snapshot_id, product_id, payload) VALUES (?, ?, ?)",
                    (snapshot_id, product.product_id, product.model_dump_json()),
                )
            for offer in document.offers:
                connection.execute(
                    "INSERT OR IGNORE INTO offers (snapshot_id, product_id, payload) VALUES (?, ?, ?)",
                    (snapshot_id, offer.product_id, offer.model_dump_json()),
                )
    finally:
        connection.close()
    return snapshot_id


def load_catalog(db_path: Path, snapshot_id: str | None = None) -> CatalogSnapshot:
    if not db_path.exists():
        raise FileNotFoundError(db_path)
    connection = _open(db_path)
    try:
        if snapshot_id is None:
            row = connection.execute(
                "SELECT snapshot_id FROM catalog_snapshots ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
            if row is None:
                raise ValueError("catalog contains no snapshots")
            snapshot_id = row[0]
        elif not connection.execute("SELECT 1 FROM catalog_snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone():
            raise ValueError("unknown catalog snapshot")
        products = tuple(
            CatalogItem.model_validate_json(row[0])
            for row in connection.execute(
                "SELECT payload FROM products WHERE snapshot_id=? ORDER BY product_id", (snapshot_id,)
            )
        )
        offers = {
            o.product_id: o
            for row in connection.execute("SELECT payload FROM offers WHERE snapshot_id=?", (snapshot_id,))
            if (o := CatalogOffer.model_validate_json(row[0]))
        }
        return CatalogSnapshot(snapshot_id=snapshot_id, products=products, offers=offers)
    finally:
        connection.close()
