"""`devos docgen <type>` — generate grounded project documentation."""
from __future__ import annotations

import argparse
from pathlib import Path

from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.modules import docgen


@register
class DocgenCommand(Command):
    name = "docgen"
    help = "Generate grounded docs (readme/architecture/api/setup/changelog/decisions/milestone)."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("type", help="Doc type: " + ", ".join(docgen.DOC_TYPES) + ".")
        parser.add_argument("--project", help="Project name (default: the only registered one).")
        parser.add_argument("--output", help="Write to this file (default: stdout). Won't overwrite without --force.")
        parser.add_argument("--force", action="store_true", help="Allow overwriting an existing --output file.")
        parser.add_argument("--limit", type=int, default=docgen.DEFAULT_LIMIT,
                            help=f"Max chunks to retrieve (default {docgen.DEFAULT_LIMIT}).")

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        if not ws.is_initialized():
            print("Nothing indexed yet - run `devos index <path>` first.")
            return 0
        conn = ws.connect()
        try:
            try:
                doc = docgen.generate(conn, args.type, provider=ws.ai,
                                      project=args.project, limit=args.limit)
            except ValueError as exc:
                print(f"error: {exc}")
                return 1
        finally:
            conn.close()

        body = doc.text
        footer = self._sources_footer(doc)

        if args.output:
            target = Path(args.output)
            if target.exists() and not args.force:
                print(f"error: '{target}' exists; use --force to overwrite.")
                return 1
            target.write_text(body + footer, encoding="utf-8")
            print(f"Wrote {doc.doc_type} to {target} ({'grounded' if doc.grounded else 'ungrounded'}).")
            return 0

        print(body)
        if footer:
            print(footer, end="")
        return 0

    @staticmethod
    def _sources_footer(doc) -> str:
        if not doc.sources:
            return ""
        lines = ["\n\nSources:"]
        for s in doc.sources:
            if hasattr(s, "location"):           # RetrievedChunk (code docs)
                lines.append(f"  - {s.location}  [{s.project}]")
            elif "title" in s:                    # record dict (memory/task)
                tag = s.get("kind") or s.get("status") or "record"
                lines.append(f"  - ({tag}) {s['title']}")
        return "\n".join(lines) + "\n"
