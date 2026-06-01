"""Repository functions: all SQL for projects and files lives here.

Modules (e.g. ingest) call these helpers rather than writing SQL directly, keeping
persistence concerns in the storage layer (see docs/ARCHITECTURE.md).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- projects -------------------------------------------------------------

def upsert_project(conn: sqlite3.Connection, root_path: str, name: str) -> int:
    """Insert a project by unique root_path, or return the existing id.

    The project name is refreshed on each call; ``created_at`` is preserved.
    """
    row = conn.execute(
        "SELECT id FROM projects WHERE root_path = ?;", (root_path,)
    ).fetchone()
    if row is not None:
        conn.execute("UPDATE projects SET name = ? WHERE id = ?;", (name, row["id"]))
        return int(row["id"])

    cur = conn.execute(
        "INSERT INTO projects (name, root_path, created_at) VALUES (?, ?, ?);",
        (name, root_path, _now()),
    )
    return int(cur.lastrowid)


def touch_project_scanned(conn: sqlite3.Connection, project_id: int) -> None:
    conn.execute(
        "UPDATE projects SET last_scanned_at = ? WHERE id = ?;", (_now(), project_id)
    )


def list_projects(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return all projects with a computed ``file_count``, newest activity first."""
    return conn.execute(
        """
        SELECT p.id, p.name, p.root_path, p.created_at, p.last_scanned_at,
               (SELECT COUNT(*) FROM files f WHERE f.project_id = p.id) AS file_count
        FROM projects p
        ORDER BY COALESCE(p.last_scanned_at, p.created_at) DESC, p.id DESC;
        """
    ).fetchall()


# --- files ----------------------------------------------------------------

def file_paths(conn: sqlite3.Connection, project_id: int) -> set[str]:
    rows = conn.execute(
        "SELECT rel_path FROM files WHERE project_id = ?;", (project_id,)
    ).fetchall()
    return {r["rel_path"] for r in rows}


def upsert_file(
    conn: sqlite3.Connection,
    project_id: int,
    rel_path: str,
    lang: str | None,
    category: str,
    size: int,
    content_hash: str,
) -> str:
    """Insert or update a file row. Returns 'added', 'updated', or 'unchanged'."""
    row = conn.execute(
        "SELECT id, content_hash FROM files WHERE project_id = ? AND rel_path = ?;",
        (project_id, rel_path),
    ).fetchone()
    now = _now()

    if row is None:
        conn.execute(
            """
            INSERT INTO files
                (project_id, rel_path, lang, category, size, content_hash, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (project_id, rel_path, lang, category, size, content_hash, now),
        )
        return "added"

    if row["content_hash"] == content_hash:
        return "unchanged"

    conn.execute(
        """
        UPDATE files
        SET lang = ?, category = ?, size = ?, content_hash = ?, indexed_at = ?
        WHERE id = ?;
        """,
        (lang, category, size, content_hash, now, row["id"]),
    )
    return "updated"


def delete_files(conn: sqlite3.Connection, project_id: int, rel_paths: set[str]) -> int:
    for rel_path in rel_paths:
        conn.execute(
            "DELETE FROM files WHERE project_id = ? AND rel_path = ?;",
            (project_id, rel_path),
        )
    return len(rel_paths)


def category_breakdown(conn: sqlite3.Connection, project_id: int) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT category, COUNT(*) AS n FROM files
        WHERE project_id = ? GROUP BY category;
        """,
        (project_id,),
    ).fetchall()
    return {r["category"]: int(r["n"]) for r in rows}
