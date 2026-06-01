"""Dashboard data builders + request routing (socket-free, unit-testable).

All endpoints are read-only and reuse the existing storage/repo + modules layers
(see docs/DECISIONS.md D-0010). `server.py` wraps `route()` in an http.server handler.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from devos.modules import recall as recall_mod
from devos.storage import repo

TASK_STATUSES = ("todo", "in_progress", "blocked", "done")
STATIC_DIR = Path(__file__).parent / "static"

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml", ".ico": "image/x-icon", ".map": "application/json",
}


def _d(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


# --- data builders --------------------------------------------------------

def overview(conn: sqlite3.Connection) -> dict:
    projects = [_d(p) for p in repo.list_projects(conn)]
    tasks = [_d(t) for t in repo.list_tasks(conn)]
    memory = [_d(m) for m in repo.list_memory(conn)]

    counts = {s: 0 for s in TASK_STATUSES}
    for t in tasks:
        counts[t["status"]] = counts.get(t["status"], 0) + 1

    blocked = [t for t in tasks if t["status"] == "blocked"]

    activity = (
        [{"type": "task", "id": t["id"], "title": t["title"],
          "status": t["status"], "when": t["updated_at"]} for t in tasks]
        + [{"type": "memory", "id": m["id"], "title": m["title"],
            "kind": m["kind"], "when": m["created_at"]} for m in memory]
    )
    activity.sort(key=lambda a: a["when"] or "", reverse=True)

    in_progress = [t for t in tasks if t["status"] == "in_progress"]
    left_task = None
    if in_progress:
        left_task = max(in_progress, key=lambda t: t["updated_at"] or "")
    elif tasks:
        left_task = max(tasks, key=lambda t: t["updated_at"] or "")

    return {
        "projects": projects,
        "task_counts": counts,
        "blocked": blocked,
        "recent_activity": activity[:10],
        "where_i_left_off": {"task": left_task, "memory": memory[0] if memory else None},
    }


def projects_payload(conn: sqlite3.Connection) -> dict:
    return {"projects": [_d(p) for p in repo.list_projects(conn)]}


def tasks_payload(conn: sqlite3.Connection, *, status: str | None = None,
                  kind: str | None = None, project: str | None = None) -> dict:
    project_id = repo.project_id_by_name(conn, project) if project else None
    rows = repo.list_tasks(conn, project_id=project_id, status=status, kind=kind)
    return {"tasks": [_d(t) for t in rows]}


def memory_payload(conn: sqlite3.Connection) -> dict:
    return {"memory": [_d(m) for m in repo.list_memory(conn)]}


def recall_payload(conn: sqlite3.Connection, query: str, *, project: str | None = None) -> dict:
    result = recall_mod.recall(conn, query, project=project)
    return {
        "query": query,
        "memory": [_d(m) for m in result.memories],
        "tasks": [_d(t) for t in result.tasks],
        "code": [{"location": c.location, "project": c.project, "rel_path": c.rel_path,
                  "start_line": c.start_line, "end_line": c.end_line} for c in result.code],
    }
