"""SQLite connection factory and minimal, idempotent migration runner.

The foundation ships schema v1 (see ``schema.sql``). The version is tracked via
SQLite's ``PRAGMA user_version`` and mirrored in the ``schema_migrations`` table so
re-running :func:`initialize` is always safe.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path

SCHEMA_VERSION = 3

# Numbered migrations applied to EXISTING databases (fresh DBs use schema.sql directly).
MIGRATIONS: dict[int, list[str]] = {
    2: ["ALTER TABLE files ADD COLUMN indexed_hash TEXT;"],
    3: ["ALTER TABLE tasks ADD COLUMN priority TEXT NOT NULL DEFAULT 'medium';"],
}

# Tables surfaced in `devos status` (exists per current schema).
COUNTED_TABLES = ("projects", "files", "chunks", "tasks", "memory")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_schema_sql() -> str:
    return resources.files("devos.storage").joinpath("schema.sql").read_text(encoding="utf-8")


def connect(db_path: Path) -> sqlite3.Connection:
    """Open a connection with sane defaults (foreign keys on, row access by name)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def schema_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version;").fetchone()[0])


def initialize(db_path: Path) -> sqlite3.Connection:
    """Create or upgrade the database and return a connection (idempotent).

    Fresh databases (version 0) are built directly from ``schema.sql`` (already at the
    latest shape). Existing databases are upgraded by applying numbered ``MIGRATIONS``
    for each version between the stored version and ``SCHEMA_VERSION``.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    current = schema_version(conn)
    if current == SCHEMA_VERSION:
        return conn

    if current == 0:
        conn.executescript(_load_schema_sql())
    else:
        for version in range(current + 1, SCHEMA_VERSION + 1):
            for statement in MIGRATIONS.get(version, []):
                conn.execute(statement)

    # Defensive: ensure the bookkeeping table exists even on an unusual legacy DB.
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);"
    )
    conn.execute(
        "INSERT OR REPLACE INTO schema_migrations (version, applied_at) VALUES (?, ?);",
        (SCHEMA_VERSION, _now()),
    )
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION};")
    conn.commit()
    return conn


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Return row counts for the core tables (for `devos status`)."""
    counts: dict[str, int] = {}
    for table in COUNTED_TABLES:
        try:
            row = conn.execute(f"SELECT COUNT(*) FROM {table};").fetchone()
            counts[table] = int(row[0])
        except sqlite3.OperationalError:
            counts[table] = 0
    return counts
