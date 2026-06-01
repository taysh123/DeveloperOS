"""`devos index [path]` — refresh inventory then build/refresh the search index."""
from __future__ import annotations

import argparse
from pathlib import Path

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
