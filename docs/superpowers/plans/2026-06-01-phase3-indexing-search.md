# Phase 3 — Code Indexing & Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first, incremental code index over already-scanned projects and a ranked keyword search (`devos index` / `devos search`), structured so semantic/embedding search can be added later without redesign.

**Architecture:** A pure `chunk_text` function splits file text into line-ranged windows. `modules/index.index_project` reads each recorded file from disk, and (incrementally, keyed on a per-file `indexed_hash`) rebuilds its chunks in the `chunks` table while mirroring chunk text into the `chunks_fts` FTS5 index. Search runs an FTS5 `MATCH` (bm25-ranked, `snippet()`-excerpted) and returns a stable `SearchHit` type — the seam a future semantic strategy reuses. All SQL stays in `storage/repo.py`.

**Tech Stack:** Python 3.11+ stdlib only (`sqlite3` FTS5 + bm25, `hashlib`, `pathlib`), stdlib `unittest`, argparse CLI. No external deps, no paid APIs.

---

## Design notes (read once before starting)

- **Incremental key:** new column `files.indexed_hash` stores the sha256 of the *text the chunks were built from*. A file is re-chunked only when its current on-disk text hash differs (or it has no chunks). This is independent of `files.content_hash` (which records scan-time state).
- **Chunk text storage:** chunk text lives only in `chunks_fts.content` (FTS5 stores originals); `chunks` holds metadata (line range, tags, per-chunk `content_hash`). No duplication. Per-chunk `content_hash` is the future seam for caching embeddings by content.
- **FTS integrity:** `chunks.file_id` has `ON DELETE CASCADE`, but `chunks_fts` is not FK-linked, so deleting a file row can orphan fts rows. Always delete chunks via `repo.delete_chunks_for_file` (removes fts rows too), and run `repo.reconcile_fts` (sweeps fts rows whose `chunk_id` no longer exists) at the start of every index pass to catch cascade orphans from `ingest`.
- **FTS query safety:** never pass raw user input to `MATCH`. Tokenize on whitespace, escape `"`→`""`, wrap each token in quotes, join with spaces (implicit AND). Empty query → no results.
- **Console safety:** all CLI output and snippet markers are ASCII (`[` … `]`, `...`) — non-ASCII mojibakes on the Windows cp1252 console (learned in Phases 1–2).
- **`devos index [path]` composes scan + index:** it refreshes the inventory via `ingest.scan_project` (unless `--no-rescan`) then indexes — one command to make a project searchable. `ingest` is reused unchanged (no duplication).
- **Parallel agents:** NOT used — tasks share `schema.sql`/`repo.py`/`index.py` state and are sequential by TDD dependency; coordination overhead would exceed benefit.

## File Structure

- Modify `devos/storage/schema.sql` — add `indexed_hash` to `files`; add an index on `chunks.file_id`.
- Modify `devos/storage/db.py` — bump `SCHEMA_VERSION` to 2; add a numbered-migration runner (v1→v2 `ALTER TABLE`).
- Modify `devos/storage/repo.py` — add indexing + search SQL helpers.
- Create `devos/modules/index.py` — `Chunk`, `chunk_text`, `IndexResult`, `index_project`, `SearchHit`, `search`.
- Create `devos/commands/index_cmd.py` — `devos index`.
- Create `devos/commands/search_cmd.py` — `devos search`.
- Modify `devos/commands/__init__.py` — register the two commands.
- Create `tests/test_index.py` — chunking, indexing, incremental, search tests.
- Modify docs: `AGENT_STATE`, `ROADMAP`, `TODO`, `PROGRESS_LOG`, `CHANGELOG`, `DECISIONS` (D-0006), `KNOWN_ISSUES`, `README`, `ARCHITECTURE` (seam note).

---

### Task 1: Schema v2 — `files.indexed_hash` + upgrade-capable migration runner

**Files:**
- Modify: `devos/storage/schema.sql`
- Modify: `devos/storage/db.py`
- Test: `tests/test_index.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_index.py  (new file — header + first test)
"""Phase 3 — indexing & search tests (TDD, stdlib unittest)."""
from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from devos.cli import main
from devos.core.workspace import Workspace
from devos.modules import index as index_mod
from devos.modules import ingest
from devos.storage import db, repo


def _write(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


class TestSchemaV2(unittest.TestCase):
    def test_files_has_indexed_hash_and_version_is_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dbp = Path(tmp) / "devos.db"
            conn = db.initialize(dbp)
            try:
                self.assertEqual(db.schema_version(conn), 2)
                cols = {r["name"] for r in conn.execute("PRAGMA table_info(files);")}
                self.assertIn("indexed_hash", cols)
            finally:
                conn.close()

    def test_upgrade_from_v1_adds_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dbp = Path(tmp) / "devos.db"
            # Simulate a legacy v1 DB: create files table without indexed_hash.
            conn = db.connect(dbp)
            conn.executescript(
                "CREATE TABLE files (id INTEGER PRIMARY KEY, project_id INTEGER, "
                "rel_path TEXT, content_hash TEXT);"
            )
            conn.execute("PRAGMA user_version = 1;")
            conn.commit()
            conn.close()

            conn = db.initialize(dbp)  # should migrate v1 -> v2
            try:
                self.assertEqual(db.schema_version(conn), 2)
                cols = {r["name"] for r in conn.execute("PRAGMA table_info(files);")}
                self.assertIn("indexed_hash", cols)
            finally:
                conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_index.TestSchemaV2 -v`
Expected: FAIL — `schema_version` is 1 / `indexed_hash` not in columns.

- [ ] **Step 3: Implement schema + migration runner**

In `devos/storage/schema.sql`, add `indexed_hash` to the `files` table and an index after it:

```sql
    indexed_hash TEXT,          -- sha256 of the text the current chunks were built from
    indexed_at   TEXT,
    UNIQUE (project_id, rel_path)
);

CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_id);
```
(Insert `indexed_hash` line immediately before the existing `indexed_at` line inside `CREATE TABLE files`; add the `CREATE INDEX` after the `chunks` table definition.)

In `devos/storage/db.py`, replace the version constant and `initialize`:

```python
SCHEMA_VERSION = 2

# Numbered migrations applied to EXISTING databases (fresh DBs use schema.sql directly).
MIGRATIONS: dict[int, list[str]] = {
    2: ["ALTER TABLE files ADD COLUMN indexed_hash TEXT;"],
}


def initialize(db_path: Path) -> sqlite3.Connection:
    """Create or upgrade the database and return a connection (idempotent)."""
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

    conn.execute(
        "INSERT OR REPLACE INTO schema_migrations (version, applied_at) VALUES (?, ?);",
        (SCHEMA_VERSION, _now()),
    )
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION};")
    conn.commit()
    return conn
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_index.TestSchemaV2 -v`
Expected: PASS (both tests).

- [ ] **Step 5: Run full suite (no regressions)**

Run: `python -m unittest discover -s tests`
Expected: OK (27 tests: 25 prior + 2 new).

- [ ] **Step 6: Commit**

```bash
git add devos/storage/schema.sql devos/storage/db.py tests/test_index.py
git commit -m "Phase 3: schema v2 (files.indexed_hash) + upgrade-capable migration runner"
```

---

### Task 2: `chunk_text` — pure line-window chunking

**Files:**
- Create: `devos/modules/index.py`
- Test: `tests/test_index.py`

- [ ] **Step 1: Write the failing test**

```python
class TestChunking(unittest.TestCase):
    def test_splits_into_line_windows(self) -> None:
        text = "\n".join(f"line{i}" for i in range(1, 121))  # 120 lines
        chunks = index_mod.chunk_text(text, max_lines=50)
        self.assertEqual(len(chunks), 3)
        self.assertEqual((chunks[0].start_line, chunks[0].end_line), (1, 50))
        self.assertEqual((chunks[1].start_line, chunks[1].end_line), (51, 100))
        self.assertEqual((chunks[2].start_line, chunks[2].end_line), (101, 120))
        self.assertTrue(chunks[0].content.startswith("line1"))
        self.assertIn("line50", chunks[0].content)

    def test_empty_text_yields_no_chunks(self) -> None:
        self.assertEqual(index_mod.chunk_text(""), [])
        self.assertEqual(index_mod.chunk_text("   \n  \n"), [])

    def test_single_short_file_is_one_chunk(self) -> None:
        chunks = index_mod.chunk_text("a\nb\nc", max_lines=50)
        self.assertEqual(len(chunks), 1)
        self.assertEqual((chunks[0].start_line, chunks[0].end_line), (1, 3))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_index.TestChunking -v`
Expected: FAIL — `cannot import name 'index'` / `chunk_text` undefined.

- [ ] **Step 3: Implement `chunk_text`**

```python
# devos/modules/index.py
"""Code indexing & search: chunking, incremental FTS5 indexing, keyword search.

Local-first and incremental. Structured so a future semantic-search strategy can
return the same `SearchHit` type without redesign (see docs/DECISIONS.md D-0006).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_index.TestChunking -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add devos/modules/index.py tests/test_index.py
git commit -m "Phase 3: pure line-window chunking (chunk_text)"
```

---

### Task 3: Repository helpers for indexing

**Files:**
- Modify: `devos/storage/repo.py`
- Test: `tests/test_index.py` (covered indirectly via Task 4; add one direct test below)

- [ ] **Step 1: Write the failing test**

```python
class TestRepoIndexHelpers(unittest.TestCase):
    def _conn(self, tmp: str):
        return db.initialize(Path(tmp) / "devos.db")

    def test_insert_and_count_and_delete_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = self._conn(tmp)
            try:
                pid = repo.upsert_project(conn, "/x", "x")
                repo.upsert_file(conn, pid, "a.py", "python", "backend", 3, "h1")
                fid = conn.execute(
                    "SELECT id FROM files WHERE project_id=? AND rel_path='a.py';", (pid,)
                ).fetchone()["id"]

                cid = repo.insert_chunk(conn, fid, 1, 2, "backend,python", "ch1", "print(1)")
                self.assertEqual(repo.file_chunk_count(conn, fid), 1)
                self.assertEqual(
                    conn.execute("SELECT content FROM chunks_fts WHERE chunk_id=?;",
                                 (cid,)).fetchone()["content"],
                    "print(1)",
                )

                repo.delete_chunks_for_file(conn, fid)
                self.assertEqual(repo.file_chunk_count(conn, fid), 0)
                self.assertIsNone(
                    conn.execute("SELECT 1 FROM chunks_fts WHERE chunk_id=?;",
                                 (cid,)).fetchone()
                )
            finally:
                conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_index.TestRepoIndexHelpers -v`
Expected: FAIL — `repo.insert_chunk` undefined.

- [ ] **Step 3: Implement repo helpers (append to `devos/storage/repo.py`)**

```python
# --- indexing: chunks --------------------------------------------------------

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


def set_file_indexed_hash(conn: sqlite3.Connection, file_id: int, value: str) -> None:
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_index.TestRepoIndexHelpers -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add devos/storage/repo.py tests/test_index.py
git commit -m "Phase 3: storage helpers for chunks + fts integrity (reconcile)"
```

---

### Task 4: `index_project` — incremental indexing service

**Files:**
- Modify: `devos/modules/index.py`
- Test: `tests/test_index.py`

- [ ] **Step 1: Write the failing tests**

```python
class IndexTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._prev = os.environ.get("DEVOS_HOME")
        self._home = tempfile.TemporaryDirectory()
        os.environ["DEVOS_HOME"] = self._home.name
        self.ws = Workspace.load()
        self.ws.initialize().close()
        self._proj = tempfile.TemporaryDirectory()
        self.root = Path(self._proj.name)
        _write(self.root, "server/app.py", "\n".join(f"row{i}" for i in range(60)))
        _write(self.root, "src/util.ts", "export const token = 'abc';")

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("DEVOS_HOME", None)
        else:
            os.environ["DEVOS_HOME"] = self._prev
        self._home.cleanup()
        self._proj.cleanup()


class TestIndexProject(IndexTestCase):
    def test_first_index_creates_chunks(self) -> None:
        conn = self.ws.connect()
        try:
            pid = ingest.scan_project(conn, self.root).project_id
            result = index_mod.index_project(conn, pid)
            self.assertGreaterEqual(result.indexed_files, 2)
            chunks, files = repo.chunk_stats(conn, pid)
            self.assertGreater(chunks, 0)
            self.assertGreaterEqual(files, 2)
        finally:
            conn.close()

    def test_reindex_unchanged_is_noop(self) -> None:
        conn = self.ws.connect()
        try:
            pid = ingest.scan_project(conn, self.root).project_id
            index_mod.index_project(conn, pid)
            chunks_before, _ = repo.chunk_stats(conn, pid)
            result = index_mod.index_project(conn, pid)
            self.assertEqual(result.indexed_files, 0)
            self.assertEqual(result.unchanged_files, 2)
            chunks_after, _ = repo.chunk_stats(conn, pid)
            self.assertEqual(chunks_after, chunks_before)
        finally:
            conn.close()

    def test_modified_file_is_reindexed(self) -> None:
        conn = self.ws.connect()
        try:
            pid = ingest.scan_project(conn, self.root).project_id
            index_mod.index_project(conn, pid)
            _write(self.root, "src/util.ts", "export const token = 'changed';\nconst y = 2;")
            ingest.scan_project(conn, self.root)
            result = index_mod.index_project(conn, pid)
            self.assertEqual(result.indexed_files, 1)
            self.assertEqual(result.unchanged_files, 1)
        finally:
            conn.close()

    def test_deleted_file_chunks_are_removed(self) -> None:
        conn = self.ws.connect()
        try:
            pid = ingest.scan_project(conn, self.root).project_id
            index_mod.index_project(conn, pid)
            (self.root / "src/util.ts").unlink()
            ingest.scan_project(conn, self.root)  # prunes the file row (chunks cascade)
            index_mod.index_project(conn, pid)     # reconcile_fts cleans fts orphans
            orphans = conn.execute(
                "SELECT COUNT(*) FROM chunks_fts WHERE chunk_id NOT IN (SELECT id FROM chunks);"
            ).fetchone()[0]
            self.assertEqual(orphans, 0)
        finally:
            conn.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_index.TestIndexProject -v`
Expected: FAIL — `index_project` / `IndexResult` undefined.

- [ ] **Step 3: Implement `IndexResult` + `index_project` (append to `devos/modules/index.py`)**

```python
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
        if not reindex_all and f["indexed_hash"] == cur_hash and f["chunk_count"]:
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_index.TestIndexProject -v`
Expected: PASS (all four).

- [ ] **Step 5: Commit**

```bash
git add devos/modules/index.py tests/test_index.py
git commit -m "Phase 3: incremental index_project (hash-keyed re-chunk + fts mirror)"
```

---

### Task 5: `SearchHit` + `search` — bm25 keyword search

**Files:**
- Modify: `devos/storage/repo.py` (add `search_chunks`)
- Modify: `devos/modules/index.py` (add `SearchHit`, `search`, `build_match_query`)
- Test: `tests/test_index.py`

- [ ] **Step 1: Write the failing tests**

```python
class TestMatchQuery(unittest.TestCase):
    def test_tokens_are_quoted_and_anded(self) -> None:
        self.assertEqual(index_mod.build_match_query("auth login"), '"auth" "login"')

    def test_special_chars_are_escaped_not_injected(self) -> None:
        q = index_mod.build_match_query('def(x): "y"')
        # produces a valid quoted FTS string; no bare quotes/operators leak through
        self.assertNotIn('("', q)
        self.assertTrue(q.startswith('"'))

    def test_empty_query_is_empty(self) -> None:
        self.assertEqual(index_mod.build_match_query("   "), "")


class TestSearch(IndexTestCase):
    def setUp(self) -> None:
        super().setUp()
        _write(self.root, "src/auth/login.py", "def authenticate(token):\n    return verify(token)")
        conn = self.ws.connect()
        try:
            pid = ingest.scan_project(conn, self.root).project_id
            index_mod.index_project(conn, pid)
        finally:
            conn.close()

    def test_search_finds_token_with_location(self) -> None:
        conn = self.ws.connect()
        try:
            hits = index_mod.search(conn, "authenticate")
            self.assertTrue(hits)
            top = hits[0]
            self.assertEqual(top.rel_path, "src/auth/login.py")
            self.assertGreaterEqual(top.start_line, 1)
            self.assertIn("authenticate", top.snippet.lower())
        finally:
            conn.close()

    def test_no_match_returns_empty(self) -> None:
        conn = self.ws.connect()
        try:
            self.assertEqual(index_mod.search(conn, "zzz_no_such_token_qqq"), [])
        finally:
            conn.close()

    def test_special_char_query_does_not_raise(self) -> None:
        conn = self.ws.connect()
        try:
            index_mod.search(conn, 'def(token):')  # must not raise sqlite errors
        finally:
            conn.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_index.TestMatchQuery tests.test_index.TestSearch -v`
Expected: FAIL — `build_match_query` / `search` undefined.

- [ ] **Step 3a: Add `search_chunks` to `devos/storage/repo.py`**

```python
# --- search ------------------------------------------------------------------

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


def project_id_by_name(conn: sqlite3.Connection, name: str) -> int | None:
    row = conn.execute("SELECT id FROM projects WHERE name = ? ORDER BY id LIMIT 1;",
                       (name,)).fetchone()
    return int(row["id"]) if row else None
```

- [ ] **Step 3b: Add `SearchHit`, `build_match_query`, `search` to `devos/modules/index.py`**

```python
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


def build_match_query(query: str) -> str:
    """Turn free text into a safe FTS5 MATCH string: AND of quoted tokens."""
    tokens = query.split()
    return " ".join('"' + t.replace('"', '""') + '"' for t in tokens)


def search(conn, query: str, *, project: str | None = None, limit: int = 10) -> list[SearchHit]:
    """Keyword search over the index. Returns ranked SearchHits (best first).

    This is the stable result type a future semantic strategy will also return,
    so callers (CLI now, Q&A in Phase 4) never need to change (see D-0006).
    """
    match_query = build_match_query(query)
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_index.TestMatchQuery tests.test_index.TestSearch -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add devos/storage/repo.py devos/modules/index.py tests/test_index.py
git commit -m "Phase 3: bm25 keyword search with safe FTS query + SearchHit seam"
```

---

### Task 6: `devos index` command

**Files:**
- Create: `devos/commands/index_cmd.py`
- Modify: `devos/commands/__init__.py`
- Test: `tests/test_index.py`

- [ ] **Step 1: Write the failing test**

```python
class TestIndexCli(IndexTestCase):
    def _run(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(argv))
        return code, buf.getvalue()

    def test_index_command_reports_chunks(self) -> None:
        code, out = self._run("index", str(self.root))
        self.assertEqual(code, 0)
        self.assertIn("chunk", out.lower())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_index.TestIndexCli -v`
Expected: FAIL — argparse: invalid choice `index`.

- [ ] **Step 3: Implement the command**

```python
# devos/commands/index_cmd.py
"""`devos index [path]` — refresh inventory then build/refresh the search index."""
from __future__ import annotations

import argparse

from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.modules import index as index_mod
from devos.modules import ingest
from devos.storage import repo


@register
class IndexCommand(Command):
    name = "index"
    help = "Scan (refresh) a project then build/refresh its searchable index."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("path", nargs="?", default=".", help="Project folder (default: current dir).")
        parser.add_argument("--name", help="Project name (default: folder name).")
        parser.add_argument("--no-rescan", action="store_true",
                            help="Index the existing inventory without re-scanning first.")
        parser.add_argument("--reindex-all", action="store_true",
                            help="Rebuild all chunks even if unchanged.")

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        ws.initialize().close()
        conn = ws.connect()
        try:
            if args.no_rescan:
                from pathlib import Path
                root = str(Path(args.path).resolve())
                project = conn.execute(
                    "SELECT id, name FROM projects WHERE root_path = ?;", (root,)
                ).fetchone()
                if project is None:
                    print(f"error: '{root}' is not a scanned project. Run `devos scan` first.")
                    return 1
                project_id, name = project["id"], project["name"]
            else:
                try:
                    scan = ingest.scan_project(conn, args.path, name=args.name)
                except (NotADirectoryError, FileNotFoundError) as exc:
                    print(f"error: {exc}")
                    return 1
                project_id, name = scan.project_id, scan.project_name

            result = index_mod.index_project(conn, project_id, reindex_all=args.reindex_all)
            chunks, files = repo.chunk_stats(conn, project_id)
        finally:
            conn.close()

        print(f"Indexed '{name}'")
        print(f"  files    : {result.total_files} "
              f"({result.indexed_files} (re)indexed, {result.unchanged_files} unchanged, "
              f"{result.skipped_files} skipped)")
        print(f"  chunks   : {chunks} across {files} files "
              f"(+{result.chunks_written} written this run)")
        return 0
```

Register in `devos/commands/__init__.py` (add after the existing imports):

```python
from devos.commands import index_cmd as _index_cmd  # noqa: F401
from devos.commands import search_cmd as _search_cmd  # noqa: F401
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_index.TestIndexCli -v`
Expected: FAIL still — `search_cmd` import error (created in Task 7). Temporarily comment the `_search_cmd` import, run, expect PASS, then restore in Task 7. (Or do Task 7 before re-running.)

- [ ] **Step 5: Commit (after Task 7 so the import resolves)**

Deferred — committed at the end of Task 7.

---

### Task 7: `devos search` command

**Files:**
- Create: `devos/commands/search_cmd.py`
- Test: `tests/test_index.py`

- [ ] **Step 1: Write the failing test**

```python
class TestSearchCli(IndexTestCase):
    def _run(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(argv))
        return code, buf.getvalue()

    def test_search_after_index(self) -> None:
        _write(self.root, "src/auth/login.py", "def authenticate(token):\n    return token")
        self._run("index", str(self.root))
        code, out = self._run("search", "authenticate")
        self.assertEqual(code, 0)
        self.assertIn("login.py", out)

    def test_search_no_results_message(self) -> None:
        self._run("index", str(self.root))
        code, out = self._run("search", "zzz_nope_qqq")
        self.assertEqual(code, 0)
        self.assertIn("No matches", out)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_index.TestSearchCli -v`
Expected: FAIL — argparse: invalid choice `search`.

- [ ] **Step 3: Implement the command**

```python
# devos/commands/search_cmd.py
"""`devos search <query>` — ranked keyword search over the index."""
from __future__ import annotations

import argparse

from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.modules import index as index_mod


@register
class SearchCommand(Command):
    name = "search"
    help = "Search indexed code/docs by keyword (ranked, with file:line references)."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("query", nargs="+", help="Search terms (implicit AND).")
        parser.add_argument("--project", help="Limit to a project by name.")
        parser.add_argument("--limit", type=int, default=10, help="Max results (default 10).")

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        query = " ".join(args.query)
        if not ws.is_initialized():
            print("Nothing indexed yet - run `devos index <path>` first.")
            return 0
        conn = ws.connect()
        try:
            hits = index_mod.search(conn, query, project=args.project, limit=args.limit)
        finally:
            conn.close()

        if not hits:
            print(f"No matches for '{query}'.")
            return 0

        print(f"{len(hits)} result(s) for '{query}':")
        for i, h in enumerate(hits, 1):
            snippet = " ".join(h.snippet.split())
            print(f"  {i}. {h.location}  [{h.project}]")
            print(f"     {snippet}")
        return 0
```

- [ ] **Step 4: Ensure both commands are registered, run tests**

Confirm both `_index_cmd` and `_search_cmd` imports are present in `devos/commands/__init__.py`.
Run: `python -m unittest tests.test_index.TestIndexCli tests.test_index.TestSearchCli -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add devos/commands/index_cmd.py devos/commands/search_cmd.py devos/commands/__init__.py tests/test_index.py
git commit -m "Phase 3: devos index + devos search commands"
```

---

### Task 8: Verification, dogfood, docs/state sync

**Files:**
- Modify: `docs/AGENT_STATE.md`, `docs/ROADMAP.md`, `docs/TODO.md`, `docs/PROGRESS_LOG.md`,
  `docs/CHANGELOG.md`, `docs/DECISIONS.md`, `docs/KNOWN_ISSUES.md`, `docs/ARCHITECTURE.md`, `README.md`

- [ ] **Step 1: Full verification (verification-before-completion skill)**

Run: `python -m unittest discover -s tests -v`
Expected: OK — all tests pass (25 prior + ~17 new ≈ 42).

- [ ] **Step 2: Dogfood on this repo (isolated home)**

```powershell
$env:DEVOS_HOME = Join-Path $env:TEMP "devos_p3"; Remove-Item -Recurse -Force $env:DEVOS_HOME -ErrorAction SilentlyContinue
devos index . --name DeveloperOS
devos index . --name DeveloperOS   # second run: expect mostly "unchanged"
devos search scan_project
devos search "fts5"
Remove-Item -Recurse -Force $env:DEVOS_HOME
```
Expected: first index writes chunks; second reports files unchanged & 0 chunks written; searches return hits in `devos/modules/ingest.py` / `devos/storage/...` with line ranges.

- [ ] **Step 3: Add DECISION D-0006** (indexing/chunking architecture + semantic seam) to `docs/DECISIONS.md`.

- [ ] **Step 4: Update state docs** — mark Phase 3 ✅ (ROADMAP), set Phase 4 as next but DO NOT start it; refresh AGENT_STATE (phase, milestone, next step, completed list), TODO (check off Phase 3), PROGRESS_LOG (new session entry), CHANGELOG (index/search added), KNOWN_ISSUES (line-window chunking is not AST-aware; keyword-only search), README (command table), ARCHITECTURE (note the SearchHit/embeddings seam under "Provider abstraction"/data model). Update memory pointer.

- [ ] **Step 5: Final commit**

```bash
git add docs README.md
git commit -m "Phase 3: docs/state sync + D-0006 (indexing architecture & semantic seam)"
```

---

## Self-Review

**Spec coverage:** (1) chunking → Task 2; (2) FTS5 indexing → Tasks 3–4; (3) incremental reindex via content hash → Task 4 (`indexed_hash`); (4) `devos index` → Task 6; (5) `devos search <query>` → Task 7; (6) ranked results with file/line → Task 5 (`bm25` + `SearchHit.location`) surfaced in Task 7. Local-first / no paid APIs / stdlib-only → honored throughout. Future-semantic-without-redesign → `SearchHit` type + per-chunk `content_hash` + D-0006 seam.

**Placeholder scan:** none — every code step contains complete code; commands and SQL are concrete.

**Type consistency:** `Chunk(start_line,end_line,content[,content_hash])`, `IndexResult(indexed_files/unchanged_files/skipped_files/chunks_written/total_files)`, `SearchHit(project,rel_path,start_line,end_line,score,snippet,tags,chunk_id,location)`, `repo.insert_chunk/delete_chunks_for_file/reconcile_fts/chunk_stats/search_chunks/project_id_by_name/get_project/list_files/set_file_indexed_hash/file_chunk_count` — used consistently across Tasks 3–7. `index_mod.search/build_match_query/index_project/chunk_text` names match between definitions and CLI/test callers.

**Note on Task 6/7 ordering:** the `_search_cmd` import is added in Task 6 but `search_cmd.py` is created in Task 7; commit for Task 6 is deferred to the end of Task 7 so the package always imports cleanly at commit points.
