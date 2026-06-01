"""`devos debug [text] [--file F]` — grounded root-cause analysis of an error/trace/log."""
from __future__ import annotations

import argparse
import sys

from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.modules import debug as debug_mod


@register
class DebugCommand(Command):
    name = "debug"
    help = "Diagnose an error / stack trace / log (paste as arg, --file, or pipe via stdin)."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("text", nargs="*", help="The error/trace text (or use --file/stdin).")
        parser.add_argument("--file", help="Read the trace/log from this file.")
        parser.add_argument("--project", help="Limit retrieval/location to a project by name.")
        parser.add_argument("--limit", type=int, default=debug_mod.DEFAULT_DEBUG_LIMIT,
                            help=f"Max related chunks (default {debug_mod.DEFAULT_DEBUG_LIMIT}).")

    def _read_trace(self, args: argparse.Namespace) -> str | None:
        if args.text:
            return " ".join(args.text)
        if args.file:
            try:
                return open(args.file, "r", encoding="utf-8", errors="ignore").read()
            except OSError as exc:
                print(f"error: cannot read --file: {exc}")
                return None
        if not sys.stdin.isatty():
            data = sys.stdin.read()
            return data if data.strip() else None
        return None

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        if not ws.is_initialized():
            print("Nothing indexed yet - run `devos index <path>` first.")
            return 0
        trace_text = self._read_trace(args)
        if not trace_text or not trace_text.strip():
            print("error: provide a trace via an argument, --file, or piped stdin.")
            return 1

        conn = ws.connect()
        try:
            diag = debug_mod.diagnose(conn, trace_text, provider=ws.ai,
                                      project=args.project, limit=args.limit)
        finally:
            conn.close()

        print("Observed evidence:")
        if diag.error_type or diag.error_message:
            label = diag.error_type or "error"
            print(f"  - {label}: {diag.error_message or ''}".rstrip())
        if diag.located_frames:
            for lf in diag.located_frames:
                loc = lf.chunk.location if lf.chunk else f"{lf.rel_path}:{lf.frame.line}"
                print(f"  - located {loc}  [{lf.project}]")
        else:
            print("  - no referenced files found in the index")
        print(f"Confidence: {diag.confidence}")
        print()
        print(diag.analysis)
        if diag.sources:
            print("\nSources:")
            seen = set()
            for s in diag.sources:
                if s.location in seen:
                    continue
                seen.add(s.location)
                print(f"  - {s.location}  [{s.project}]")
        return 0
