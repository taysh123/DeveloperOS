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


def delete_project(conn: sqlite3.Connection, project_id: int) -> int:
    """Remove a project and all DeveloperOS data derived from it (index-only — never the
    files on disk). Relies on the ``ON DELETE CASCADE`` foreign keys (files -> chunks,
    tasks, memory; foreign_keys pragma is enabled in ``db.connect``) and then reconciles
    the FTS mirror, which is a virtual table not covered by cascades."""
    cur = conn.execute("DELETE FROM projects WHERE id = ?;", (project_id,))
    reconcile_fts(conn)
    conn.commit()
    return cur.rowcount


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


def _like(term: str) -> str:
    """Escape LIKE wildcards in user text; pair with ESCAPE '\\' in the query."""
    return "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


# --- tasks ----------------------------------------------------------------

_TASK_COLS = "id, project_id, title, kind, status, priority, milestone, notes, created_at, updated_at"


def create_task(conn: sqlite3.Connection, project_id: int | None, title: str, *,
                kind: str = "task", status: str = "todo", priority: str = "medium",
                milestone: str | None = None, notes: str | None = None) -> int:
    now = _now()
    cur = conn.execute(
        "INSERT INTO tasks (project_id, title, kind, status, priority, milestone, notes, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);",
        (project_id, title, kind, status, priority, milestone, notes, now, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def get_task(conn: sqlite3.Connection, task_id: int) -> sqlite3.Row | None:
    return conn.execute(
        f"SELECT {_TASK_COLS} FROM tasks WHERE id = ?;", (task_id,)
    ).fetchone()


def list_tasks(conn: sqlite3.Connection, *, project_id: int | None = None,
               status: str | None = None, kind: str | None = None,
               milestone: str | None = None, include_global: bool = False) -> list[sqlite3.Row]:
    clauses, params = [], []
    if project_id is not None:
        if include_global:
            clauses.append("(project_id = ? OR project_id IS NULL)"); params.append(project_id)
        else:
            clauses.append("project_id = ?"); params.append(project_id)
    if status is not None:
        clauses.append("status = ?"); params.append(status)
    if kind is not None:
        clauses.append("kind = ?"); params.append(kind)
    if milestone is not None:
        clauses.append("milestone = ?"); params.append(milestone)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return conn.execute(
        f"SELECT {_TASK_COLS} FROM tasks{where} ORDER BY id;", params
    ).fetchall()


_TASK_UPDATABLE = {"title", "kind", "status", "priority", "milestone", "notes"}


def update_task(conn: sqlite3.Connection, task_id: int, **fields) -> int:
    sets = [(k, v) for k, v in fields.items() if k in _TASK_UPDATABLE and v is not None]
    if not sets:
        return 0
    assignments = ", ".join(f"{k} = ?" for k, _ in sets) + ", updated_at = ?"
    params = [v for _, v in sets] + [_now(), task_id]
    cur = conn.execute(f"UPDATE tasks SET {assignments} WHERE id = ?;", params)
    conn.commit()
    return cur.rowcount


def delete_task(conn: sqlite3.Connection, task_id: int) -> int:
    cur = conn.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))
    conn.commit()
    return cur.rowcount


def search_tasks(conn: sqlite3.Connection, query: str, *, project_id: int | None = None,
                 limit: int = 10) -> list[sqlite3.Row]:
    clauses = ["(title LIKE ? ESCAPE '\\' OR IFNULL(notes,'') LIKE ? ESCAPE '\\')"]
    params: list[object] = [_like(query), _like(query)]
    if project_id is not None:
        clauses.append("project_id = ?"); params.append(project_id)
    params.append(limit)
    return conn.execute(
        f"SELECT {_TASK_COLS} FROM tasks WHERE {' AND '.join(clauses)} "
        f"ORDER BY id DESC LIMIT ?;", params
    ).fetchall()


# --- job leads (career) ---------------------------------------------------

JOB_STATUSES = ("saved", "applied", "interview", "offer", "rejected", "closed")
_JOB_COLS = "id, company, role, url, status, notes, created_at, updated_at"


def create_job(conn: sqlite3.Connection, company: str, *, role: str | None = None,
               url: str | None = None, status: str = "saved", notes: str | None = None) -> int:
    now = _now()
    cur = conn.execute(
        "INSERT INTO job_leads (company, role, url, status, notes, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?);",
        (company, role, url, status, notes, now, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def get_job(conn: sqlite3.Connection, job_id: int) -> sqlite3.Row | None:
    return conn.execute(f"SELECT {_JOB_COLS} FROM job_leads WHERE id = ?;", (job_id,)).fetchone()


def list_jobs(conn: sqlite3.Connection, *, status: str | None = None) -> list[sqlite3.Row]:
    if status is not None:
        return conn.execute(
            f"SELECT {_JOB_COLS} FROM job_leads WHERE status = ? ORDER BY id;", (status,)
        ).fetchall()
    return conn.execute(f"SELECT {_JOB_COLS} FROM job_leads ORDER BY id;").fetchall()


_JOB_UPDATABLE = {"company", "role", "url", "status", "notes"}


def update_job(conn: sqlite3.Connection, job_id: int, **fields) -> int:
    sets = [(k, v) for k, v in fields.items() if k in _JOB_UPDATABLE and v is not None]
    if not sets:
        return 0
    assignments = ", ".join(f"{k} = ?" for k, _ in sets) + ", updated_at = ?"
    params = [v for _, v in sets] + [_now(), job_id]
    cur = conn.execute(f"UPDATE job_leads SET {assignments} WHERE id = ?;", params)
    conn.commit()
    return cur.rowcount


def delete_job(conn: sqlite3.Connection, job_id: int) -> int:
    cur = conn.execute("DELETE FROM job_leads WHERE id = ?;", (job_id,))
    conn.commit()
    return cur.rowcount


# --- memory ---------------------------------------------------------------

_MEM_COLS = "id, project_id, kind, title, body, tags, created_at"


def create_memory(conn: sqlite3.Connection, project_id: int | None, *, kind: str = "note",
                  title: str, body: str, tags: str | None = None) -> int:
    """Insert a memory; idempotent on (project_id, title, body) -> returns existing id."""
    existing = conn.execute(
        "SELECT id FROM memory WHERE IFNULL(project_id,-1) = IFNULL(?,-1) "
        "AND title = ? AND body = ?;",
        (project_id, title, body),
    ).fetchone()
    if existing is not None:
        return int(existing["id"])
    cur = conn.execute(
        "INSERT INTO memory (project_id, kind, title, body, tags, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?);",
        (project_id, kind, title, body, tags, _now()),
    )
    conn.commit()
    return int(cur.lastrowid)


def get_memory(conn: sqlite3.Connection, memory_id: int) -> sqlite3.Row | None:
    return conn.execute(
        f"SELECT {_MEM_COLS} FROM memory WHERE id = ?;", (memory_id,)
    ).fetchone()


_MEMORY_UPDATABLE = {"title", "body", "kind", "tags"}


def update_memory(conn: sqlite3.Connection, memory_id: int, **fields) -> int:
    """Update whitelisted fields of a memory (note). Returns rowcount.

    Mirrors ``update_task``: only ``_MEMORY_UPDATABLE`` keys with non-None values are
    written, via parameterized SQL. The memory table has no ``updated_at`` column."""
    sets = [(k, v) for k, v in fields.items() if k in _MEMORY_UPDATABLE and v is not None]
    if not sets:
        return 0
    assignments = ", ".join(f"{k} = ?" for k, _ in sets)
    params = [v for _, v in sets] + [memory_id]
    cur = conn.execute(f"UPDATE memory SET {assignments} WHERE id = ?;", params)
    conn.commit()
    return cur.rowcount


def list_memory(conn: sqlite3.Connection, *, project_id: int | None = None,
                kind: str | None = None, include_global: bool = False) -> list[sqlite3.Row]:
    clauses, params = [], []
    if project_id is not None:
        if include_global:
            clauses.append("(project_id = ? OR project_id IS NULL)"); params.append(project_id)
        else:
            clauses.append("project_id = ?"); params.append(project_id)
    if kind is not None:
        clauses.append("kind = ?"); params.append(kind)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return conn.execute(
        f"SELECT {_MEM_COLS} FROM memory{where} ORDER BY id DESC;", params
    ).fetchall()


def delete_memory(conn: sqlite3.Connection, memory_id: int) -> int:
    cur = conn.execute("DELETE FROM memory WHERE id = ?;", (memory_id,))
    conn.commit()
    return cur.rowcount


def search_memory(conn: sqlite3.Connection, query: str, *, project_id: int | None = None,
                  limit: int = 10) -> list[sqlite3.Row]:
    clauses = ["(title LIKE ? ESCAPE '\\' OR body LIKE ? ESCAPE '\\' "
               "OR IFNULL(tags,'') LIKE ? ESCAPE '\\')"]
    params: list[object] = [_like(query), _like(query), _like(query)]
    if project_id is not None:
        clauses.append("project_id = ?"); params.append(project_id)
    params.append(limit)
    return conn.execute(
        f"SELECT {_MEM_COLS} FROM memory WHERE {' AND '.join(clauses)} "
        f"ORDER BY id DESC LIMIT ?;", params
    ).fetchall()


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


# --- retrieval (Q&A) ------------------------------------------------------

def get_chunk_content(conn: sqlite3.Connection, chunk_id: int) -> str | None:
    row = conn.execute(
        "SELECT content FROM chunks_fts WHERE chunk_id = ?;", (chunk_id,)
    ).fetchone()
    return row["content"] if row else None


def get_file_chunks(
    conn: sqlite3.Connection, project_id: int, rel_path: str
) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT c.id AS chunk_id, c.start_line, c.end_line, fts.content
        FROM chunks c
        JOIN files f ON f.id = c.file_id
        JOIN chunks_fts fts ON fts.chunk_id = c.id
        WHERE f.project_id = ? AND f.rel_path = ?
        ORDER BY c.start_line;
        """,
        (project_id, rel_path),
    ).fetchall()


def find_project_for_path(conn: sqlite3.Connection, abs_path: str) -> sqlite3.Row | None:
    """Return the project whose root_path contains abs_path (longest match wins).

    Both sides are canonicalized with realpath (not just abspath): scan stores the
    root resolve()d to its long form, while callers may pass a Windows 8.3 short
    alias (e.g. the CI runner's C:\\Users\\RUNNERA~1 TEMP) or a symlinked path —
    realpath makes those compare equal. Nonexistent paths pass through unchanged.
    """
    import os as _os
    target = _os.path.normcase(_os.path.realpath(abs_path))
    best = None
    best_len = -1
    for p in conn.execute("SELECT id, name, root_path FROM projects;").fetchall():
        root = _os.path.normcase(_os.path.realpath(p["root_path"]))
        if target == root or target.startswith(root + _os.sep):
            if len(root) > best_len:
                best, best_len = p, len(root)
    return best


def find_file_by_path(
    conn: sqlite3.Connection, project_id: int, path: str
) -> sqlite3.Row | None:
    """Resolve a (possibly partial / OS-style) path to an indexed file row.

    Tries exact rel_path, then a path-suffix / basename match. Index-only: never
    touches the filesystem (security: trace-supplied paths must not cause file reads).
    """
    norm = path.replace("\\", "/").lstrip("./")
    row = conn.execute(
        "SELECT id, rel_path FROM files WHERE project_id = ? AND rel_path = ?;",
        (project_id, norm),
    ).fetchone()
    if row is not None:
        return row
    base = norm.rsplit("/", 1)[-1]
    rows = conn.execute(
        "SELECT id, rel_path FROM files WHERE project_id = ? "
        "AND (rel_path = ? OR rel_path LIKE ?) ORDER BY LENGTH(rel_path);",
        (project_id, base, "%/" + base),
    ).fetchall()
    for r in rows:
        if r["rel_path"].endswith(norm):
            return r
    return rows[0] if rows else None


def top_files(conn: sqlite3.Connection, project_id: int, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT f.rel_path, f.category, f.lang,
               (SELECT COUNT(*) FROM chunks c WHERE c.file_id = f.id) AS chunk_count
        FROM files f WHERE f.project_id = ?
        ORDER BY chunk_count DESC, f.rel_path LIMIT ?;
        """,
        (project_id, limit),
    ).fetchall()
