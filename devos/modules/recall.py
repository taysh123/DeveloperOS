"""Recall across memory, tasks, and project code.

Retrieval-only and offline: groups matching memory + task rows (SQL LIKE) with related
code chunks (reusing qa.retrieve -> index.search FTS). No AI provider call, so no new
prompt-injection surface (see docs/SECURITY.md sec. 5). An empty query lists recent
memory/tasks (no code). See docs/DECISIONS.md D-0009.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from devos.modules import qa
from devos.modules.qa import RetrievedChunk
from devos.storage import repo


@dataclass
class RecallResult:
    memories: list = field(default_factory=list)   # sqlite3.Row
    tasks: list = field(default_factory=list)       # sqlite3.Row
    code: list[RetrievedChunk] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not (self.memories or self.tasks or self.code)


def recall(conn, query: str, *, project: str | None = None,
           limit: int = qa.DEFAULT_RETRIEVAL) -> RecallResult:
    """Recall memory, tasks, and code for a query (empty query -> recent memory/tasks)."""
    project_id = repo.project_id_by_name(conn, project) if project else None
    if project and project_id is None:
        return RecallResult()

    q = query.strip()
    if not q:
        return RecallResult(
            memories=repo.list_memory(conn, project_id=project_id)[:limit],
            tasks=repo.list_tasks(conn, project_id=project_id)[:limit],
            code=[],
        )

    return RecallResult(
        memories=repo.search_memory(conn, q, project_id=project_id, limit=limit),
        tasks=repo.search_tasks(conn, q, project_id=project_id, limit=limit),
        code=qa.retrieve(conn, q, project=project, limit=limit),
    )
