"""`devos scan <path>` — ingest a project folder into the local inventory."""
from __future__ import annotations

import argparse

from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.modules import ingest


@register
class ScanCommand(Command):
    name = "scan"
    help = "Scan a project folder and record/refresh its file inventory."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("path", nargs="?", default=".", help="Project folder (default: current dir).")
        parser.add_argument("--name", help="Project name (default: folder name).")
        parser.add_argument(
            "--no-prune",
            action="store_true",
            help="Keep inventory rows for files that no longer exist on disk.",
        )

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        # Scanning implies wanting to use DeveloperOS here; ensure storage exists (idempotent).
        ws.initialize().close()
        conn = ws.connect()
        try:
            result = ingest.scan_project(
                conn, args.path, name=args.name, prune=not args.no_prune
            )
        except (NotADirectoryError, FileNotFoundError) as exc:
            print(f"error: {exc}")
            return 1
        finally:
            conn.close()

        print(f"Scanned '{result.project_name}'  ({result.root})")
        print(f"  files    : {result.total} "
              f"(+{result.added} added, ~{result.updated} updated, "
              f"={result.unchanged} unchanged, -{result.removed} removed, "
              f"{result.skipped} skipped)")
        if result.by_category:
            print("  by type  :")
            for category, count in sorted(result.by_category.items()):
                print(f"    - {category:<9}: {count}")
        return 0
