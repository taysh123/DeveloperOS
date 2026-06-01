"""`devos meeting summarize <file>` — grounded summary + action items from a transcript."""
from __future__ import annotations

import argparse
from pathlib import Path

from devos.commands.base import Command, register
from devos.core.workspace import Workspace
from devos.modules import meeting


@register
class MeetingCommand(Command):
    name = "meeting"
    help = "Meeting/transcript tools (summarize a local transcript or notes file)."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        sub = parser.add_subparsers(dest="meeting_action", metavar="<action>")
        p_sum = sub.add_parser("summarize", help="Summarize a transcript/notes file.")
        p_sum.add_argument("file", help="Path to the transcript/notes text file.")

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        if not ws.is_initialized():
            print("Nothing here yet - run `devos init` first.")
            return 0
        if getattr(args, "meeting_action", None) != "summarize":
            print("usage: devos meeting summarize <file>")
            return 1
        try:
            # utf-8-sig strips a leading BOM (common on Windows-saved files).
            text = open(args.file, "r", encoding="utf-8-sig", errors="ignore").read()
        except OSError as exc:
            print(f"error: cannot read transcript file: {exc}")
            return 1

        summary = meeting.summarize(text, provider=ws.ai, source_label=Path(args.file).name)
        print(summary.text)
        if summary.grounded:
            print(f"\nSource: {summary.source_label}")
        return 0
