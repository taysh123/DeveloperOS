"""Dashboard data builders + request routing (socket-free, unit-testable).

All endpoints are read-only and reuse the existing storage/repo + modules layers
(see docs/DECISIONS.md D-0010). `server.py` wraps `route()` in an http.server handler.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from devos import __version__, settings as settings_mod
from devos.modules import career as career_mod
from devos.modules import debug as debug_mod
from devos.modules import index as index_mod
from devos.modules import ingest
from devos.modules import learning
from devos.modules import meeting as meeting_mod
from devos.modules import qa
from devos.modules import recall as recall_mod
from devos.providers.ai import available_providers
from devos.storage import repo

ROADMAP_PHASE = "v0.6.0 · Feature-complete dashboard + first real AI provider (Ollama, local)"
DASHBOARD_MATURITY = (
    "Stable — full CLI parity (Home, Tasks, Notes, Search & Ask, Debug, Projects, Learn, "
    "Career, Meeting, Settings)"
)

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
    ".png": "image/png", ".webmanifest": "application/manifest+json",
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


def _interview_prep(name: str, key_files: list[dict], categories: dict) -> list[str]:
    """A friendly, deterministic study/interview checklist (no provider call, offline)."""
    prep = [f"Explain in about a minute what “{name}” does and who it's for."]
    if key_files:
        prep.append(f"Walk through {key_files[0]['rel_path']} and what it's responsible for.")
    top_cats = [c for c, _ in sorted(categories.items(), key=lambda kv: -kv[1])][:3]
    if top_cats:
        prep.append("Describe how the main parts fit together: " + ", ".join(top_cats) + ".")
    prep.append("Pick one feature and trace it from start to finish.")
    prep.append("What would you improve or add next, and why?")
    return prep


def study_payload(conn: sqlite3.Connection, ws, project_id: int, *, n: int = 6) -> dict | None:
    """Project Deep Dive bundle: facts + key files + grounded overview/questions + prep.

    Pure aggregation over existing modules (no new analysis engine): qa.explain for the
    plain-language overview, learning.quiz for grounded study questions, repo for structure."""
    row = next((p for p in repo.list_projects(conn) if p["id"] == project_id), None)
    if row is None:
        return None
    name = row["name"]
    categories = repo.category_breakdown(conn, project_id)
    key_files = [_d(f) for f in repo.top_files(conn, project_id, 8)]

    overview = qa.explain(conn, None, provider=ws.ai, project=name)
    target = key_files[0]["rel_path"] if key_files else name
    quiz = learning.quiz(conn, target, provider=ws.ai, project=name, n=n)

    return {
        "project": _d(row),
        "categories": categories,
        "key_files": key_files,
        "overview": _answer_dict(overview),
        "questions": {"n": quiz.n, "text": quiz.text, "grounded": quiz.grounded,
                      "provider": quiz.provider,
                      "sources": [{"location": s.location, "project": s.project,
                                   "rel_path": s.rel_path, "start_line": s.start_line,
                                   "end_line": s.end_line} for s in quiz.sources]},
        "interview_prep": _interview_prep(name, key_files, categories),
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


def _chunk_sources(sources) -> list[dict]:
    """Serialize RetrievedChunk sources (shared by the learning endpoints)."""
    return [{"location": s.location, "project": s.project, "rel_path": s.rel_path,
             "start_line": s.start_line, "end_line": s.end_line} for s in sources]


def learn_payload(conn: sqlite3.Connection, ws, target: str, *,
                  level: str = "intermediate", project: str | None = None) -> dict:
    """Grounded, leveled explanation of a file (file mode) or topic (topic mode)."""
    lesson = learning.learn(conn, target, provider=ws.ai, level=level, project=project)
    return {"topic": lesson.topic, "level": lesson.level, "text": lesson.text,
            "grounded": lesson.grounded, "provider": lesson.provider,
            "sources": _chunk_sources(lesson.sources)}


def quiz_payload(conn: sqlite3.Connection, ws, target: str, *,
                 n: int = 5, project: str | None = None) -> dict:
    """``n`` grounded review questions about a file/topic."""
    qz = learning.quiz(conn, target, provider=ws.ai, n=n, project=project)
    return {"topic": qz.topic, "n": qz.n, "text": qz.text, "grounded": qz.grounded,
            "provider": qz.provider, "sources": _chunk_sources(qz.sources)}


def exercise_payload(conn: sqlite3.Connection, ws, target: str, *,
                     n: int = 3, project: str | None = None) -> dict:
    """``n`` grounded practice exercises for a file/topic."""
    ex = learning.exercise(conn, target, provider=ws.ai, n=n, project=project)
    return {"topic": ex.topic, "n": ex.n, "text": ex.text, "grounded": ex.grounded,
            "provider": ex.provider, "sources": _chunk_sources(ex.sources)}


def grade_payload(conn: sqlite3.Connection, ws, target: str, *, answer: str,
                  question: str | None = None, project: str | None = None) -> dict:
    """Evaluate a learner's answer about a file/topic against grounded code context."""
    g = learning.grade(conn, target, answer=answer, provider=ws.ai,
                       question=question, project=project)
    return {"topic": g.topic, "text": g.text, "grounded": g.grounded,
            "provider": g.provider, "sources": _chunk_sources(g.sources)}


# --- career (slice 8) -----------------------------------------------------

def jobs_payload(conn: sqlite3.Connection, *, status: str | None = None) -> dict:
    return {"jobs": [_d(j) for j in repo.list_jobs(conn, status=status)]}


def interview_payload(conn: sqlite3.Connection, ws, job_id: int, *, n: int = 5) -> dict:
    """Grounded interview-prep questions from a job lead's stored notes (reuse career.interview_prep)."""
    prep = career_mod.interview_prep(conn, job_id, provider=ws.ai, n=n)
    return {"job_id": prep.job_id, "n": n, "text": prep.text,
            "grounded": prep.grounded, "provider": prep.provider, "sources": prep.sources}


def cv_payload(conn: sqlite3.Connection, cv_text: str, *, target_text: str,
               target_label: str = "") -> dict:
    """Deterministic, offline CV-vs-target keyword coverage (reuse career.analyze_cv). Not persisted."""
    a = career_mod.analyze_cv(cv_text, target_text, target_label=target_label)
    return {"matched": sorted(a.matched), "missing": sorted(a.missing),
            "matched_count": len(a.matched), "target_count": len(a.target_keywords),
            "coverage": round(a.coverage, 3), "target_label": a.target_label}


# --- meeting (slice 9) ------------------------------------------------------

def meeting_payload(ws, text: str, *, source_label: str = "") -> dict:
    """Summarize pasted meeting notes/transcript + extract action-item candidates.

    Reuses ``modules/meeting``: the summary goes through the provider seam (mock by
    default, offline); ``action_items`` are extracted deterministically from the
    transcript itself (never from model output) so the "create tasks" bridge works
    with AI off. The transcript is NOT persisted (same rule as the CV text, D-0025).
    """
    summary = meeting_mod.summarize(text, provider=ws.ai, source_label=source_label)
    return {
        "source_label": summary.source_label,
        "text": summary.text,
        "grounded": summary.grounded,
        "provider": summary.provider,
        "action_items": meeting_mod.extract_action_items(text),
    }


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


# --- system status & settings (slice 5) -----------------------------------

def _provider_catalog(*, with_key_status: bool) -> list[dict]:
    """The provider catalog with runtime flags. `available` = registered/usable today;
    `key_present` (opt-in) is a boolean only — the key value is never read or returned."""
    registered = set(available_providers())
    out = []
    for p in settings_mod.PROVIDERS:
        item = dict(p)
        item["available"] = p["id"] in registered
        if with_key_status:
            item["key_present"] = settings_mod.key_present(p["id"])
        out.append(item)
    return out


def system_payload(conn: sqlite3.Connection, ws) -> dict:
    """A plain-language snapshot of how DeveloperOS is running (slice 5 System status)."""
    stored = settings_mod.load(ws.config.data_dir)
    effective = settings_mod.effective_provider_name(stored.ai_provider, stored.ai_enabled)
    return {
        "local_first": True,
        "offline": True,  # default + only-registered provider is the offline mock
        "ai_enabled": stored.ai_enabled,
        "provider_selected": stored.ai_provider,
        "provider_effective": effective,
        "version": __version__,
        "roadmap_phase": ROADMAP_PHASE,
        "indexed_project_count": len(repo.list_projects(conn)),
        "dashboard_maturity": DASHBOARD_MATURITY,
        "providers": _provider_catalog(with_key_status=False),
    }


def settings_payload(ws) -> dict:
    """Current AI settings + the provider catalog (with key-detection booleans)."""
    stored = settings_mod.load(ws.config.data_dir)
    return {
        "ai_enabled": stored.ai_enabled,
        "ai_provider": stored.ai_provider,
        "providers": _provider_catalog(with_key_status=True),
    }


def update_settings_action(ws, body: dict) -> Response:
    """Persist the two non-secret preferences. Any `api_key`/`endpoint` in the body is
    ignored — only `ai_enabled`/`ai_provider` are read, so a secret can never be stored."""
    ai_enabled = body.get("ai_enabled")
    if ai_enabled is not None and not isinstance(ai_enabled, bool):
        return _bad("ai_enabled must be true or false")
    provider = body.get("ai_provider")
    if provider is not None and provider not in settings_mod.PROVIDER_IDS:
        return _bad(f"provider must be one of {', '.join(settings_mod.PROVIDER_IDS)}")
    try:
        settings_mod.save(ws.config.data_dir, ai_enabled=ai_enabled, ai_provider=provider)
    except ValueError as exc:
        return _bad(str(exc))
    return _json(settings_payload(ws))


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


def _require_id(body: dict, noun: str) -> "tuple[int | None, Response | None]":
    """Validate a positive integer ``id`` from a delete request body."""
    rid = body.get("id")
    if not isinstance(rid, int) or isinstance(rid, bool) or rid <= 0:
        return None, _bad(f"a valid {noun} id is required")
    return rid, None


def delete_task_action(conn: sqlite3.Connection, body: dict) -> Response:
    tid, err = _require_id(body, "task")
    if err:
        return err
    if repo.get_task(conn, tid) is None:
        return _json({"error": f"no task #{tid}"}, 404)
    return _json({"deleted": repo.delete_task(conn, tid)})


def delete_note_action(conn: sqlite3.Connection, body: dict) -> Response:
    mid, err = _require_id(body, "note")
    if err:
        return err
    if repo.get_memory(conn, mid) is None:
        return _json({"error": f"no note #{mid}"}, 404)
    return _json({"deleted": repo.delete_memory(conn, mid)})


def delete_project_action(conn: sqlite3.Connection, body: dict) -> Response:
    """Remove a project from DeveloperOS. Cascades to that project's tasks, notes, file
    inventory, chunks, and FTS rows (see repo.delete_project) — but never deletes the
    user's files on disk."""
    pid, err = _require_id(body, "project")
    if err:
        return err
    if repo.get_project(conn, pid) is None:
        return _json({"error": f"no project #{pid}"}, 404)
    return _json({"deleted": repo.delete_project(conn, pid)})


# --- career: job leads (slice 8) ------------------------------------------

def _clean_optional(value, label: str, cap: int) -> "tuple[str | None, Response | None]":
    """Validate an optional length-capped string field; '' -> None."""
    if value is None:
        return None, None
    s = str(value).strip()
    if not s:
        return None, None
    if len(s) > cap:
        return None, _bad(f"{label} is too long (max {cap} characters)")
    return s, None


def create_job_action(conn: sqlite3.Connection, body: dict) -> Response:
    company = str(body.get("company") or "").strip()
    if not company:
        return _bad("a company name is required")
    if len(company) > MAX_TITLE:
        return _bad(f"company is too long (max {MAX_TITLE} characters)")
    status = body.get("status") or "saved"
    if status not in repo.JOB_STATUSES:
        return _bad(f"status must be one of {', '.join(repo.JOB_STATUSES)}")
    role, err = _clean_optional(body.get("role"), "role", MAX_TITLE)
    if err:
        return err
    url, err = _clean_optional(body.get("url"), "link", MAX_TITLE)
    if err:
        return err
    notes, err = _clean_optional(body.get("notes"), "notes", MAX_BODY)
    if err:
        return err
    jid = repo.create_job(conn, company, role=role, url=url, status=status, notes=notes)
    return _json({"id": jid}, 201)


def update_job_action(conn: sqlite3.Connection, body: dict) -> Response:
    jid, err = _require_id(body, "job")
    if err:
        return err
    if repo.get_job(conn, jid) is None:
        return _json({"error": f"no job #{jid}"}, 404)
    fields: dict = {}
    if body.get("company") is not None:
        company = str(body["company"]).strip()
        if not company:
            return _bad("company cannot be empty")
        if len(company) > MAX_TITLE:
            return _bad(f"company is too long (max {MAX_TITLE} characters)")
        fields["company"] = company
    if body.get("status") is not None:
        if body["status"] not in repo.JOB_STATUSES:
            return _bad(f"status must be one of {', '.join(repo.JOB_STATUSES)}")
        fields["status"] = body["status"]
    for key, cap in (("role", MAX_TITLE), ("url", MAX_TITLE), ("notes", MAX_BODY)):
        if body.get(key) is not None:
            val, verr = _clean_optional(body.get(key), key, cap)
            if verr:
                return verr
            fields[key] = val or ""
    if not fields:
        return _bad("no updatable fields provided")
    return _json({"updated": repo.update_job(conn, jid, **fields)})


def delete_job_action(conn: sqlite3.Connection, body: dict) -> Response:
    jid, err = _require_id(body, "job")
    if err:
        return err
    if repo.get_job(conn, jid) is None:
        return _json({"error": f"no job #{jid}"}, 404)
    return _json({"deleted": repo.delete_job(conn, jid)})


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
    "/api/tasks/delete": delete_task_action,
    "/api/notes/create": create_note_action,
    "/api/notes/update": update_note_action,
    "/api/notes/delete": delete_note_action,
    "/api/projects/scan": scan_project_action,
    "/api/projects/delete": delete_project_action,
    "/api/jobs/create": create_job_action,
    "/api/jobs/update": update_job_action,
    "/api/jobs/delete": delete_job_action,
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
                if path == "/api/settings":
                    # read-vs-DB note: writes a non-secret JSON file (not SQLite), so it
                    # needs `ws` (data_dir), not `conn` — handled inline like /api/debug.
                    return update_settings_action(ws, body or {})
                if path == "/api/grade":
                    # read-only AI (reuses ws.ai); POST because the learner's answer is
                    # multi-line free text. Inline like /api/debug.
                    b = body or {}
                    target = str(b.get("target") or "").strip()
                    if not target:
                        return _bad("a file path or topic is required")
                    answer = b.get("answer")
                    if not isinstance(answer, str) or not answer.strip():
                        return _bad("write an answer to grade")
                    return _json(grade_payload(conn, ws, target, answer=answer,
                                               question=b.get("question"), project=b.get("project")))
                if path == "/api/cv":
                    # deterministic, offline CV keyword check; POST because the CV is multi-line
                    # free text. Inline like /api/grade. The CV text is NOT persisted.
                    b = body or {}
                    cv_text = b.get("cv_text")
                    if not isinstance(cv_text, str) or not cv_text.strip():
                        return _bad("paste your CV text to check")
                    if len(cv_text) > MAX_BODY:
                        return _bad(f"CV text is too long (max {MAX_BODY} characters)")
                    target_text = b.get("target_text")
                    label = ""
                    if isinstance(target_text, str) and target_text.strip():
                        target = target_text
                        if len(target) > MAX_BODY:
                            return _bad(f"job description is too long (max {MAX_BODY} characters)")
                    elif b.get("job_id") is not None:
                        jid = b.get("job_id")
                        if not isinstance(jid, int) or isinstance(jid, bool) or jid <= 0:
                            return _bad("a valid job id is required")
                        job = repo.get_job(conn, jid)
                        if job is None:
                            return _json({"error": f"no job #{jid}"}, 404)
                        if not (job["notes"] and job["notes"].strip()):
                            return _bad("that job has no notes to compare against — add notes first")
                        target = job["notes"]
                        label = f"{job['company']} — {job['role'] or 'role'}"
                    else:
                        return _bad("choose a job to compare against, or paste a job description")
                    return _json(cv_payload(conn, cv_text, target_text=target, target_label=label))
                if path == "/api/meeting":
                    # read-only AI (reuses ws.ai); POST because the transcript is multi-line
                    # free text. Inline like /api/debug. The transcript is NOT persisted.
                    b = body or {}
                    text = b.get("text")
                    if not isinstance(text, str) or not text.strip():
                        return _bad("paste meeting notes or a transcript to summarize")
                    if len(text) > MAX_BODY:
                        return _bad(f"transcript is too long (max {MAX_BODY} characters)")
                    label = str(b.get("source_label") or "").strip()[:MAX_TITLE]
                    return _json(meeting_payload(ws, text, source_label=label))
                action = _POST_ACTIONS.get(path)
                if action is None:
                    return _json({"error": "not found", "path": path}, 404)
                return action(conn, body or {})
            if path == "/api/health":
                return _json({"ok": True})
            if path == "/api/system":
                return _json(system_payload(conn, ws))
            if path == "/api/settings":
                return _json(settings_payload(ws))
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
            if path == "/api/projects/study":
                pid = query.get("id")
                if pid is None or not str(pid).isdigit():
                    return _bad("a valid project id is required")
                n = _int(query.get("n"), default=6, lo=1, hi=20)
                study = study_payload(conn, ws, int(pid), n=n)
                if study is None:
                    return _json({"error": f"no project #{pid}"}, 404)
                return _json(study)
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
            if path == "/api/learn":
                target = query.get("target", "").strip()
                if not target:
                    return _bad("a file path or topic is required")
                level = query.get("level") or "intermediate"
                if level not in learning.LEVELS:
                    return _bad(f"level must be one of {', '.join(learning.LEVELS)}")
                return _json(learn_payload(conn, ws, target, level=level,
                                           project=query.get("project")))
            if path == "/api/quiz":
                target = query.get("target", "").strip()
                if not target:
                    return _bad("a file path or topic is required")
                n = _int(query.get("n"), default=5, lo=1, hi=20)
                return _json(quiz_payload(conn, ws, target, n=n, project=query.get("project")))
            if path == "/api/exercise":
                target = query.get("target", "").strip()
                if not target:
                    return _bad("a file path or topic is required")
                n = _int(query.get("n"), default=3, lo=1, hi=10)
                return _json(exercise_payload(conn, ws, target, n=n, project=query.get("project")))
            if path == "/api/jobs":
                status = query.get("status")
                if status is not None and status not in repo.JOB_STATUSES:
                    return _bad(f"status must be one of {', '.join(repo.JOB_STATUSES)}")
                return _json(jobs_payload(conn, status=status))
            if path == "/api/jobs/interview":
                jid = query.get("id")
                if jid is None or not str(jid).isdigit():
                    return _bad("a valid job id is required")
                if repo.get_job(conn, int(jid)) is None:
                    return _json({"error": f"no job #{jid}"}, 404)
                n = _int(query.get("n"), default=5, lo=1, hi=15)
                return _json(interview_payload(conn, ws, int(jid), n=n))
        finally:
            conn.close()
    return _json({"error": "not found", "path": path}, 404)


def _int(value, *, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default
