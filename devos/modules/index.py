"""Code indexing & search: chunking, incremental FTS5 indexing, keyword search.

Local-first and incremental. Structured so a future semantic-search strategy can
return the same `SearchHit` type without redesign (see docs/DECISIONS.md D-0006).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from devos.storage import repo

DEFAULT_CHUNK_LINES = 50
MAX_INDEX_BYTES = 2_000_000


@dataclass
class Chunk:
    start_line: int
    end_line: int
    content: str

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()


def chunk_text(text: str, *, max_lines: int = DEFAULT_CHUNK_LINES) -> list[Chunk]:
    """Split text into non-overlapping windows of at most ``max_lines`` lines.

    Returns [] for empty/whitespace-only text. Line numbers are 1-based inclusive.
    """
    if not text.strip():
        return []
    lines = text.splitlines()
    chunks: list[Chunk] = []
    for start in range(0, len(lines), max_lines):
        window = lines[start:start + max_lines]
        chunks.append(Chunk(
            start_line=start + 1,
            end_line=start + len(window),
            content="\n".join(window),
        ))
    return chunks


@dataclass
class IndexResult:
    project_id: int
    indexed_files: int = 0      # files (re)chunked this run
    unchanged_files: int = 0
    skipped_files: int = 0      # unreadable/binary/oversized
    chunks_written: int = 0

    @property
    def total_files(self) -> int:
        return self.indexed_files + self.unchanged_files


def _read_text(path: Path, max_bytes: int) -> str | None:
    try:
        if path.stat().st_size > max_bytes:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:4096]:
        return None
    return data.decode("utf-8", errors="ignore")


def index_project(
    conn, project_id: int, *,
    max_lines: int = DEFAULT_CHUNK_LINES,
    max_bytes: int = MAX_INDEX_BYTES,
    reindex_all: bool = False,
) -> IndexResult:
    """(Re)build the chunk/FTS index for a project. Incremental via files.indexed_hash."""
    project = repo.get_project(conn, project_id)
    if project is None:
        raise ValueError(f"Unknown project id: {project_id}")
    root = Path(project["root_path"])
    repo.reconcile_fts(conn)  # clean any fts orphans from prior cascade deletes

    result = IndexResult(project_id=project_id)
    for f in repo.list_files(conn, project_id):
        text = _read_text(root / f["rel_path"], max_bytes)
        if text is None:
            if f["chunk_count"]:
                repo.delete_chunks_for_file(conn, f["id"])
                repo.set_file_indexed_hash(conn, f["id"], None)
            result.skipped_files += 1
            continue

        cur_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        # A matching indexed_hash means the content is byte-identical to what we last
        # indexed, so the stored chunks are already correct (including 0 chunks for an
        # empty file). Do not gate on chunk_count, or empty files re-process every run.
        if not reindex_all and f["indexed_hash"] == cur_hash:
            result.unchanged_files += 1
            continue

        repo.delete_chunks_for_file(conn, f["id"])
        tags = ",".join(t for t in (f["category"], f["lang"]) if t)
        for ch in chunk_text(text, max_lines=max_lines):
            repo.insert_chunk(conn, f["id"], ch.start_line, ch.end_line,
                              tags, ch.content_hash, ch.content)
            result.chunks_written += 1
        repo.set_file_indexed_hash(conn, f["id"], cur_hash)
        result.indexed_files += 1

    conn.commit()
    return result


@dataclass
class SearchHit:
    project: str
    rel_path: str
    start_line: int
    end_line: int
    score: float
    snippet: str
    tags: str | None
    chunk_id: int

    @property
    def location(self) -> str:
        return f"{self.rel_path}:{self.start_line}-{self.end_line}"


def build_match_query(query: str, *, op: str = "AND") -> str:
    """Turn free text into a safe FTS5 MATCH string.

    op="AND" -> all tokens required (implicit AND). op="OR" -> any token (better for
    natural-language questions). Tokens are quote-escaped; never inject raw input.
    """
    tokens = ['"' + t.replace('"', '""') + '"' for t in query.split()]
    if not tokens:
        return ""
    joiner = " OR " if op.upper() == "OR" else " "
    return joiner.join(tokens)


def search(conn, query: str, *, project: str | None = None, limit: int = 10,
           op: str = "AND") -> list[SearchHit]:
    """Keyword search over the index. Returns ranked SearchHits (best first).

    This is the stable result type a future semantic strategy will also return, so
    callers (CLI now, Q&A in Phase 4) never need to change (see docs/DECISIONS.md D-0006).
    """
    match_query = build_match_query(query, op=op)
    if not match_query:
        return []
    project_id = repo.project_id_by_name(conn, project) if project else None
    if project and project_id is None:
        return []
    rows = repo.search_chunks(conn, match_query, project_id=project_id, limit=limit)
    return [
        SearchHit(
            project=r["project"], rel_path=r["rel_path"],
            start_line=r["start_line"], end_line=r["end_line"],
            score=float(r["score"]), snippet=r["snippet"],
            tags=r["tags"], chunk_id=r["chunk_id"],
        )
        for r in rows
    ]
