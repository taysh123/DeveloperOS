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
