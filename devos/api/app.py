"""Dashboard data builders + request routing (socket-free, unit-testable).

All endpoints are read-only and reuse the existing storage/repo + modules layers
(see docs/DECISIONS.md D-0010). `server.py` wraps `route()` in an http.server handler.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from devos.modules import debug as debug_mod
from devos.modules import index as index_mod
from devos.modules import ingest
from devos.modules import qa
from devos.modules import recall as recall_mod
from devos.storage import repo

TASK_STATUSES = ("todo", "in_progress", "blocked", "done")
TASK_KINDS = ("task", "bug", "feature")
TASK_PRIORITIES = ("low", "medium", "high")
MEMORY_KINDS = ("decision", "summary", "preference", "note")
MAX_TITLE = 500
MAX_BODY = 20000
STATIC_DIR = Path(__file__).parent / "static"

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml", ".ico": "image/x-icon", ".map": "application/json",
}


def _d(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


@dataclass
class Response:
    status: int
    content_type: str
    body: bytes


def _json(obj, status: int = 200) -> Response:
    return Response(status, "application/json; charset=utf-8",
                    json.dumps(obj).encode("utf-8"))


def _serve_static(rel: str) -> Response:
    """Serve a file from STATIC_DIR, rejecting path traversal."""
    target = (STATIC_DIR / rel).resolve()
    try:
        target.relative_to(STATIC_DIR.resolve())
    except ValueError:
        return _json({"error": "not found"}, 404)
    if not target.is_file():
        return _json({"error": "not found"}, 404)
    ctype = _CONTENT_TYPES.get(target.suffix.lower(), "application/octet-stream")
    return Response(200, ctype, target.read_bytes())


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


def project_detail(conn: sqlite3.Connection, project_id: int) -> dict | None:
    """Full overview for one project, or None if it doesn't exist."""
    row = next((p for p in repo.list_projects(conn) if p["id"] == project_id), None)
    if row is None:
        return None
    chunks, indexed_files = repo.chunk_stats(conn, project_id)
    return {
        "project": _d(row),
        "by_category": repo.category_breakdown(conn, project_id),
        "index": {"chunks": chunks, "indexed_files": indexed_files},
    }


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


def search_payload(conn: sqlite3.Connection, query: str, *,
                   project: str | None = None, limit: int = 10) -> dict:
    hits = index_mod.search(conn, query, project=project, limit=limit, op="OR")
    return {"query": query, "results": [
        {"location": h.location, "project": h.project, "rel_path": h.rel_path,
         "start_line": h.start_line, "end_line": h.end_line,
         "snippet": h.snippet, "score": h.score} for h in hits]}


def _answer_dict(ans) -> dict:
    """Serialize a qa.Answer (shared by ask + explain)."""
    return {
        "text": ans.text, "grounded": ans.grounded, "provider": ans.provider,
        "sources": [{"location": s.location, "project": s.project, "rel_path": s.rel_path,
                     "start_line": s.start_line, "end_line": s.end_line} for s in ans.sources],
    }


def ask_payload(conn: sqlite3.Connection, ws, question: str, *,
                project: str | None = None) -> dict:
    ans = qa.answer(conn, question, provider=ws.ai, project=project)
    return {"question": question, **_answer_dict(ans)}


def explain_payload(conn: sqlite3.Connection, ws, path: str | None, *,
                    project: str | None = None) -> dict:
    ans = qa.explain(conn, path or None, provider=ws.ai, project=project)
    return {"path": path or None, **_answer_dict(ans)}


def debug_payload(conn: sqlite3.Connection, ws, trace_text: str, *,
                  project: str | None = None) -> dict:
    """Diagnose a pasted error/trace/log (read-only). Reuses modules/debug.diagnose."""
    diag = debug_mod.diagnose(conn, trace_text, provider=ws.ai, project=project)
    return {
        "error_type": diag.error_type,
        "error_message": diag.error_message,
        "frames": [{"file": f.file, "line": f.line, "func": f.func} for f in diag.frames],
        "located": [{"project": lf.project, "rel_path": lf.rel_path,
                     "line": lf.frame.line, "func": lf.frame.func,
                     "has_code": lf.chunk is not None} for lf in diag.located_frames],
        "analysis": diag.analysis,
        "confidence": diag.confidence,
        "grounded": diag.grounded,
        "provider": diag.provider,
        "sources": [{"location": s.location, "project": s.project, "rel_path": s.rel_path,
                     "start_line": s.start_line, "end_line": s.end_line} for s in diag.sources],
    }


# --- write actions (POST, JSON body) --------------------------------------

def _bad(msg: str) -> Response:
    return _json({"error": msg}, 400)


def _resolve_project(conn: sqlite3.Connection, name) -> "tuple[int | None, Response | None]":
    """Resolve an optional project name to an id. Returns (id_or_None, error_or_None)."""
    if not name:
        return None, None
    pid = repo.project_id_by_name(conn, str(name))
    if pid is None:
        return None, _bad(f"unknown project '{name}'")
    return pid, None


def _clean_title(value) -> "tuple[str | None, Response | None]":
    title = str(value or "").strip()
    if not title:
        return None, _bad("title is required")
    if len(title) > MAX_TITLE:
        return None, _bad(f"title is too long (max {MAX_TITLE} characters)")
    return title, None


def create_task_action(conn: sqlite3.Connection, body: dict) -> Response:
    title, err = _clean_title(body.get("title"))
    if err:
        return err
    kind = body.get("kind") or "task"
    status = body.get("status") or "todo"
    priority = body.get("priority") or "medium"
    if kind not in TASK_KINDS:
        return _bad(f"kind must be one of {', '.join(TASK_KINDS)}")
    if status not in TASK_STATUSES:
        return _bad(f"status must be one of {', '.join(TASK_STATUSES)}")
    if priority not in TASK_PRIORITIES:
        return _bad(f"priority must be one of {', '.join(TASK_PRIORITIES)}")
    pid, err = _resolve_project(conn, body.get("project"))
    if err:
        return err
    tid = repo.create_task(conn, pid, title, kind=kind, status=status,
                           priority=priority, notes=body.get("notes"))
    return _json({"id": tid}, 201)


def update_task_action(conn: sqlite3.Connection, body: dict) -> Response:
    tid = body.get("id")
    if not isinstance(tid, int) or tid <= 0:
        return _bad("a valid task id is required")
    if repo.get_task(conn, tid) is None:
        return _json({"error": f"no task #{tid}"}, 404)
    fields: dict = {}
    if body.get("title") is not None:
        title, err = _clean_title(body.get("title"))
        if err:
            return err
        fields["title"] = title
    for key, allowed in (("status", TASK_STATUSES), ("priority", TASK_PRIORITIES),
                         ("kind", TASK_KINDS)):
        if body.get(key) is not None:
            if body[key] not in allowed:
                return _bad(f"{key} must be one of {', '.join(allowed)}")
            fields[key] = body[key]
    for key in ("milestone", "notes"):
        if body.get(key) is not None:
            fields[key] = str(body[key])
    if not fields:
        return _bad("no updatable fields provided")
    return _json({"updated": repo.update_task(conn, tid, **fields)})


def create_note_action(conn: sqlite3.Connection, body: dict) -> Response:
    title, err = _clean_title(body.get("title"))
    if err:
        return err
    text = str(body.get("body") or "").strip()
    if not text:
        return _bad("body is required")
    if len(text) > MAX_BODY:
        return _bad(f"body is too long (max {MAX_BODY} characters)")
    kind = body.get("kind") or "note"
    if kind not in MEMORY_KINDS:
        return _bad(f"kind must be one of {', '.join(MEMORY_KINDS)}")
    pid, err = _resolve_project(conn, body.get("project"))
    if err:
        return err
    mid = repo.create_memory(conn, pid, kind=kind, title=title, body=text,
                             tags=body.get("tags"))
    return _json({"id": mid}, 201)


def update_note_action(conn: sqlite3.Connection, body: dict) -> Response:
    mid = body.get("id")
    if not isinstance(mid, int) or mid <= 0:
        return _bad("a valid note id is required")
    if repo.get_memory(conn, mid) is None:
        return _json({"error": f"no note #{mid}"}, 404)
    fields: dict = {}
    if body.get("title") is not None:
        title, err = _clean_title(body.get("title"))
        if err:
            return err
        fields["title"] = title
    if body.get("body") is not None:
        text = str(body["body"]).strip()
        if not text:
            return _bad("body cannot be empty")
        if len(text) > MAX_BODY:
            return _bad(f"body is too long (max {MAX_BODY} characters)")
        fields["body"] = text
    if body.get("kind") is not None:
        if body["kind"] not in MEMORY_KINDS:
            return _bad(f"kind must be one of {', '.join(MEMORY_KINDS)}")
        fields["kind"] = body["kind"]
    if body.get("tags") is not None:
        fields["tags"] = str(body["tags"])
    if not fields:
        return _bad("no updatable fields provided")
    return _json({"updated": repo.update_memory(conn, mid, **fields)})


MAX_PATH = 4096


def scan_project_action(conn: sqlite3.Connection, body: dict) -> Response:
    """Import/scan a folder the user named, then index it so it's searchable.

    The path is untrusted: ``ingest.scan_project`` resolves + validates it as a directory
    (non-directory/missing -> friendly 400) and applies the usual ignore/size/binary rules."""
    path = body.get("path")
    if not isinstance(path, str) or not path.strip():
        return _bad("a folder path is required")
    if len(path) > MAX_PATH:
        return _bad("path is too long")
    name = body.get("name")
    if name is not None:
        name = str(name).strip() or None
        if name and len(name) > MAX_TITLE:
            return _bad(f"name is too long (max {MAX_TITLE} characters)")
    try:
        result = ingest.scan_project(conn, path.strip(), name=name)
    except (NotADirectoryError, FileNotFoundError):
        return _bad("That folder doesn't exist on this computer. Check the path and try again.")
    except OSError as exc:
        return _bad(f"Couldn't read that folder: {exc}")
    index_result = index_mod.index_project(conn, result.project_id)
    return _json({
        "project_id": result.project_id,
        "project_name": result.project_name,
        "root": result.root,
        "total": result.total,
        "added": result.added,
        "updated": result.updated,
        "unchanged": result.unchanged,
        "removed": result.removed,
        "skipped": result.skipped,
        "by_category": result.by_category,
        "indexed_chunks": index_result.chunks_written,
    }, 201)


_POST_ACTIONS = {
    "/api/tasks/create": create_task_action,
    "/api/tasks/update": update_task_action,
    "/api/notes/create": create_note_action,
    "/api/notes/update": update_note_action,
    "/api/projects/scan": scan_project_action,
}


# --- routing --------------------------------------------------------------

def route(ws, path: str, query: dict[str, str], *, method: str = "GET",
          body: dict | None = None) -> Response:
    """Map a request to a Response. JSON for /api/*, static files otherwise.

    GET endpoints are read-only; POST endpoints (in ``_POST_ACTIONS``) perform guarded
    DB writes. The HTTP boundary (``server.py``) enforces CSRF token + origin before any
    POST reaches here (see docs/SECURITY.md sec. 8)."""
    if method == "GET" and (path == "/" or path == "/index.html"):
        return _serve_static("index.html")
    if method == "GET" and path.startswith("/static/"):
        return _serve_static(path[len("/static/"):])

    if path.startswith("/api/"):
        if not ws.is_initialized():
            return _json({"error": "not initialized; run `devos init` or `devos scan`"}, 503)
        conn = ws.connect()
        try:
            if method == "POST":
                if path == "/api/debug":
                    text = (body or {}).get("trace")
                    if not isinstance(text, str) or not text.strip():
                        return _bad("paste an error, stack trace, or log to analyze")
                    return _json(debug_payload(conn, ws, text,
                                               project=(body or {}).get("project")))
                action = _POST_ACTIONS.get(path)
                if action is None:
                    return _json({"error": "not found", "path": path}, 404)
                return action(conn, body or {})
            if path == "/api/health":
                return _json({"ok": True})
            if path == "/api/overview":
                return _json(overview(conn))
            if path == "/api/projects":
                return _json(projects_payload(conn))
            if path == "/api/projects/detail":
                pid = query.get("id")
                if pid is None or not str(pid).isdigit():
                    return _bad("a valid project id is required")
                detail = project_detail(conn, int(pid))
                if detail is None:
                    return _json({"error": f"no project #{pid}"}, 404)
                return _json(detail)
            if path == "/api/tasks":
                return _json(tasks_payload(conn, status=query.get("status"),
                                           kind=query.get("kind"), project=query.get("project")))
            if path == "/api/memory":
                return _json(memory_payload(conn))
            if path == "/api/recall":
                return _json(recall_payload(conn, query.get("q", ""), project=query.get("project")))
            if path == "/api/search":
                limit = _int(query.get("limit"), default=10, lo=1, hi=50)
                return _json(search_payload(conn, query.get("q", ""),
                                            project=query.get("project"), limit=limit))
            if path == "/api/ask":
                q = query.get("q", "").strip()
                if not q:
                    return _bad("a question is required")
                return _json(ask_payload(conn, ws, q, project=query.get("project")))
            if path == "/api/explain":
                return _json(explain_payload(conn, ws, query.get("path"),
                                             project=query.get("project")))
        finally:
            conn.close()
    return _json({"error": "not found", "path": path}, 404)


def _int(value, *, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default
