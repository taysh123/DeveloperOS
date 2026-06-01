-- DeveloperOS schema (v1). Idempotent: safe to re-run.
-- Tables grow per roadmap phase; this is the foundation spine.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL
);

-- Phase 2: registered projects.
CREATE TABLE IF NOT EXISTS projects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    root_path       TEXT NOT NULL UNIQUE,
    created_at      TEXT NOT NULL,
    last_scanned_at TEXT,
    meta            TEXT NOT NULL DEFAULT '{}'   -- JSON
);

-- Phase 2: file inventory per project.
CREATE TABLE IF NOT EXISTS files (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id   INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    rel_path     TEXT NOT NULL,
    lang         TEXT,
    category     TEXT,           -- frontend|backend|db|api|auth|test|config|other
    size         INTEGER,
    content_hash TEXT,
    indexed_hash TEXT,          -- sha256 of the text the current chunks were built from
    indexed_at   TEXT,
    UNIQUE (project_id, rel_path)
);

-- Phase 3: code/doc chunks for indexing & search.
CREATE TABLE IF NOT EXISTS chunks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id      INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    start_line   INTEGER,
    end_line     INTEGER,
    tags         TEXT,
    content_hash TEXT
);

CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_id);

-- Phase 3: full-text keyword search over chunk content (FTS5).
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    content,
    chunk_id UNINDEXED
);

-- Phase 6: task/bug/feature tracking.
CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    kind        TEXT NOT NULL DEFAULT 'task',   -- task|bug|feature
    status      TEXT NOT NULL DEFAULT 'todo',   -- todo|in_progress|blocked|done
    priority    TEXT NOT NULL DEFAULT 'medium', -- low|medium|high
    milestone   TEXT,
    notes       TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

-- Phase 9 (career): tracked job leads.
CREATE TABLE IF NOT EXISTS job_leads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company     TEXT NOT NULL,
    role        TEXT,
    url         TEXT,
    status      TEXT NOT NULL DEFAULT 'saved',  -- saved|applied|interview|offer|rejected|closed
    notes       TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

-- Phase 6: memory engine entries.
CREATE TABLE IF NOT EXISTS memory (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL DEFAULT 'note',   -- decision|summary|preference|note
    title       TEXT NOT NULL,
    body        TEXT NOT NULL,
    tags        TEXT,
    created_at  TEXT NOT NULL
);
