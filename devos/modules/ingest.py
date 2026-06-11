"""Project ingestion: walk a folder, classify files, and persist an inventory.

Local-first and idempotent: re-scanning the same path updates the existing project
in place (added / updated / unchanged / removed) rather than duplicating it.

Classification is heuristic (extension + path/filename markers) and maps every file
to one of the documented buckets: frontend, backend, db, api, auth, test, config,
other. Heuristics are intentionally simple and will be refined in later phases.
"""
from __future__ import annotations

import fnmatch
import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

from devos.storage import repo

# Files larger than this (or detected as binary) are skipped — they aren't useful
# for code understanding/indexing and would bloat the store.
MAX_FILE_BYTES = 2_000_000

# Directory names never worth scanning. Combined with .gitignore patterns at scan time.
DEFAULT_IGNORE_DIRS = frozenset({
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".env", "dist", "build", ".next", ".nuxt", "out", "target", "bin", "obj",
    ".idea", ".vscode", ".devos", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".gradle", ".tox", "coverage", ".cache", "vendor", ".terraform",
})

LANG_BY_EXT = {
    ".py": "python", ".pyi": "python", ".js": "javascript", ".mjs": "javascript",
    ".cjs": "javascript", ".jsx": "jsx", ".ts": "typescript", ".tsx": "tsx",
    ".vue": "vue", ".svelte": "svelte", ".go": "go", ".rs": "rust", ".java": "java",
    ".kt": "kotlin", ".rb": "ruby", ".php": "php", ".cs": "csharp", ".cpp": "cpp",
    ".c": "c", ".h": "c", ".hpp": "cpp", ".swift": "swift", ".scala": "scala",
    ".css": "css", ".scss": "scss", ".sass": "sass", ".less": "less", ".html": "html",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml", ".ini": "ini",
    ".cfg": "ini", ".md": "markdown", ".rst": "rst", ".sql": "sql", ".prisma": "prisma",
    ".sh": "shell", ".bash": "shell", ".ps1": "powershell", ".dockerfile": "docker",
}

_FRONTEND_EXTS = {".jsx", ".tsx", ".vue", ".svelte", ".css", ".scss", ".sass", ".less", ".html"}
_BACKEND_EXTS = {".py", ".go", ".rs", ".java", ".kt", ".rb", ".php", ".cs", ".cpp", ".c",
                 ".h", ".hpp", ".swift", ".scala"}
_CONFIG_EXTS = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env", ".lock"}
_CONFIG_NAMES = {"dockerfile", "makefile", "procfile", ".gitignore", ".dockerignore",
                 ".editorconfig", ".npmrc", ".nvmrc", "requirements.txt"}
_TEST_DIR_MARKERS = {"test", "tests", "spec", "specs", "__tests__"}
_AUTH_MARKERS = ("auth", "login", "logout", "oauth", "jwt", "session", "passport", "password")
_API_DIR_MARKERS = {"api", "routes", "endpoints", "controllers", "handlers", "resolvers"}
_DB_DIR_MARKERS = {"migrations", "migration", "schema", "seeds"}


# Files that commonly hold credentials/keys. They are NEVER read, hashed, recorded,
# or indexed — skipped before the first byte is read, so a secret can never reach
# SQLite or the FTS index (docs/SECURITY.md sec. 2, "secret-aware indexing").
SECRET_FILE_PATTERNS = (
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks", "*.keystore",
    "id_rsa", "id_rsa.*", "id_dsa", "id_ecdsa", "id_ed25519", "*.ppk",
    ".netrc", ".npmrc", ".pypirc", "credentials", "credentials.json",
    "service-account*.json", "secrets.*", "*.secret",
)


def is_secret_file(name: str) -> bool:
    """True if a filename matches a known secret/credential pattern (case-insensitive)."""
    low = name.lower()
    return any(fnmatch.fnmatch(low, pat) for pat in SECRET_FILE_PATTERNS)


def _looks_like_test(parts: list[str], name: str) -> bool:
    if any(part.lower() in _TEST_DIR_MARKERS for part in parts[:-1]):
        return True
    low = name.lower()
    if low.startswith("test_") or low.endswith("_test.py"):
        return True
    # e.g. Button.test.tsx, util.spec.ts
    stem = low.rsplit(".", 1)[0]
    return stem.endswith(".test") or stem.endswith(".spec")


def classify(rel_path: str | os.PathLike[str]) -> tuple[str | None, str]:
    """Return ``(language, category)`` for a project-relative path.

    Precedence: test > config > db > auth > api > frontend/backend (by extension) > other.
    """
    p = Path(rel_path)
    parts = [part for part in p.parts]
    name = p.name
    low_name = name.lower()
    ext = p.suffix.lower()
    lang = LANG_BY_EXT.get(ext) or (LANG_BY_EXT.get("." + low_name) if "." not in name else None)
    if low_name == "dockerfile":
        lang = "docker"
    dir_parts = {part.lower() for part in parts[:-1]}

    if _looks_like_test(parts, name):
        return lang, "test"
    if ext in _CONFIG_EXTS or low_name in _CONFIG_NAMES:
        return lang, "config"
    if ext in {".sql", ".prisma"} or (dir_parts & _DB_DIR_MARKERS):
        return lang, "db"
    if any(marker in part for part in parts for marker in _AUTH_MARKERS):
        return lang, "auth"
    if dir_parts & _API_DIR_MARKERS:
        return lang, "api"
    if ext in _FRONTEND_EXTS:
        return lang, "frontend"
    if ext in _BACKEND_EXTS:
        return lang, "backend"
    return lang, "other"


def is_binary_bytes(sample: bytes) -> bool:
    """Heuristic: a NUL byte in the sampled prefix marks the file as binary."""
    return b"\x00" in sample


def _read_gitignore_patterns(root: Path) -> list[str]:
    """Read a small subset of the top-level .gitignore (no negation/nesting)."""
    gi = root / ".gitignore"
    if not gi.exists():
        return []
    patterns: list[str] = []
    for raw in gi.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        patterns.append(line.rstrip("/"))
    return patterns


def _matches_gitignore(rel_posix: str, name: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel_posix, pat) \
                or fnmatch.fnmatch(rel_posix, pat + "/*"):
            return True
    return False


@dataclass
class ScanResult:
    project_id: int
    project_name: str
    root: str
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0
    skipped: int = 0
    skipped_secrets: int = 0  # subset of `skipped`: matched SECRET_FILE_PATTERNS
    by_category: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        """Number of files currently recorded for the project."""
        return self.added + self.updated + self.unchanged


def scan_project(
    conn,
    root: str | os.PathLike[str],
    name: str | None = None,
    *,
    max_file_bytes: int = MAX_FILE_BYTES,
    prune: bool = True,
) -> ScanResult:
    """Scan ``root``, persisting/refreshing the project and its file inventory.

    Idempotent by ``root`` path (project) and ``(project, rel_path)`` (files). When
    ``prune`` is True, files that no longer exist on disk are removed from the inventory.
    """
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {root_path}")

    project_name = name or root_path.name
    project_id = repo.upsert_project(conn, str(root_path), project_name)
    existing = repo.file_paths(conn, project_id)
    gitignore = _read_gitignore_patterns(root_path)

    result = ScanResult(project_id=project_id, project_name=project_name, root=str(root_path))
    seen: set[str] = set()

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Prune ignored directories in place (also stops descent into them).
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in DEFAULT_IGNORE_DIRS
            and not _matches_gitignore(
                (Path(dirpath, d).relative_to(root_path)).as_posix(), d, gitignore
            )
        )
        for filename in sorted(filenames):
            abs_path = Path(dirpath) / filename
            rel_posix = abs_path.relative_to(root_path).as_posix()

            if _matches_gitignore(rel_posix, filename, gitignore):
                result.skipped += 1
                continue
            if is_secret_file(filename):
                # Skipped before stat/read: secret content never touches the DB/index.
                result.skipped += 1
                result.skipped_secrets += 1
                continue
            try:
                size = abs_path.stat().st_size
            except OSError:
                result.skipped += 1
                continue
            if size > max_file_bytes:
                result.skipped += 1
                continue
            try:
                data = abs_path.read_bytes()
            except OSError:
                result.skipped += 1
                continue
            if is_binary_bytes(data[:4096]):
                result.skipped += 1
                continue

            lang, category = classify(rel_posix)
            content_hash = hashlib.sha256(data).hexdigest()
            status = repo.upsert_file(
                conn, project_id, rel_posix, lang, category, size, content_hash
            )
            setattr(result, status, getattr(result, status) + 1)
            seen.add(rel_posix)

    if prune:
        missing = existing - seen
        result.removed = repo.delete_files(conn, project_id, missing)

    repo.touch_project_scanned(conn, project_id)
    result.by_category = repo.category_breakdown(conn, project_id)
    conn.commit()
    return result
