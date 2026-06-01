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


# --- indexing: chunks -----------------------------------------------------

def get_project(conn: sqlite3.Connection, project_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, name, root_path FROM projects WHERE id = ?;", (project_id,)
    ).fetchone()


def list_files(conn: sqlite3.Connection, project_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT f.id, f.rel_path, f.lang, f.category, f.indexed_hash,
               (SELECT COUNT(*) FROM chunks c WHERE c.file_id = f.id) AS chunk_count
        FROM files f WHERE f.project_id = ? ORDER BY f.rel_path;
        """,
        (project_id,),
    ).fetchall()


def set_file_indexed_hash(conn: sqlite3.Connection, file_id: int, value: str | None) -> None:
    conn.execute("UPDATE files SET indexed_hash = ? WHERE id = ?;", (value, file_id))


def file_chunk_count(conn: sqlite3.Connection, file_id: int) -> int:
    return int(conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE file_id = ?;", (file_id,)
    ).fetchone()[0])


def insert_chunk(
    conn: sqlite3.Connection, file_id: int, start_line: int, end_line: int,
    tags: str | None, content_hash: str, content: str,
) -> int:
    cur = conn.execute(
        "INSERT INTO chunks (file_id, start_line, end_line, tags, content_hash) "
        "VALUES (?, ?, ?, ?, ?);",
        (file_id, start_line, end_line, tags, content_hash),
    )
    chunk_id = int(cur.lastrowid)
    conn.execute(
        "INSERT INTO chunks_fts (content, chunk_id) VALUES (?, ?);", (content, chunk_id)
    )
    return chunk_id


def delete_chunks_for_file(conn: sqlite3.Connection, file_id: int) -> None:
    rows = conn.execute("SELECT id FROM chunks WHERE file_id = ?;", (file_id,)).fetchall()
    for r in rows:
        conn.execute("DELETE FROM chunks_fts WHERE chunk_id = ?;", (r["id"],))
    conn.execute("DELETE FROM chunks WHERE file_id = ?;", (file_id,))


def reconcile_fts(conn: sqlite3.Connection) -> int:
    """Remove fts rows whose chunk no longer exists (e.g. after file-row cascade delete)."""
    cur = conn.execute(
        "DELETE FROM chunks_fts WHERE chunk_id NOT IN (SELECT id FROM chunks);"
    )
    return cur.rowcount if cur.rowcount is not None else 0


def chunk_stats(conn: sqlite3.Connection, project_id: int) -> tuple[int, int]:
    """Return (chunk_count, indexed_file_count) for a project."""
    row = conn.execute(
        """
        SELECT COUNT(*) AS chunks,
               COUNT(DISTINCT c.file_id) AS files
        FROM chunks c JOIN files f ON f.id = c.file_id
        WHERE f.project_id = ?;
        """,
        (project_id,),
    ).fetchone()
    return int(row["chunks"]), int(row["files"])


# --- search ---------------------------------------------------------------

def project_id_by_name(conn: sqlite3.Connection, name: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM projects WHERE name = ? ORDER BY id LIMIT 1;", (name,)
    ).fetchone()
    return int(row["id"]) if row else None


def search_chunks(
    conn: sqlite3.Connection, match_query: str, *,
    project_id: int | None = None, limit: int = 10,
) -> list[sqlite3.Row]:
    sql = [
        "SELECT c.id AS chunk_id, f.rel_path, c.start_line, c.end_line, c.tags,",
        "       p.name AS project,",
        "       snippet(chunks_fts, 0, '[', ']', '...', 12) AS snippet,",
        "       bm25(chunks_fts) AS score",
        "FROM chunks_fts",
        "JOIN chunks c ON c.id = chunks_fts.chunk_id",
        "JOIN files f ON f.id = c.file_id",
        "JOIN projects p ON p.id = f.project_id",
        "WHERE chunks_fts MATCH ?",
    ]
    params: list[object] = [match_query]
    if project_id is not None:
        sql.append("AND p.id = ?")
        params.append(project_id)
    sql.append("ORDER BY bm25(chunks_fts) LIMIT ?;")
    params.append(limit)
    return conn.execute("\n".join(sql), params).fetchall()
