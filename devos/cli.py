"""DeveloperOS command-line interface.

Thin dispatcher: builds an argparse parser from the registered commands and routes
to the matching :class:`~devos.commands.base.Command`. Output is plain text for now;
richer UX (Rich/Typer) is considered in Phase 7 (see docs/DECISIONS.md D-0005).
"""
from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from devos import __version__
from devos.commands import COMMANDS
from devos.core.workspace import Workspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devos",
        description="DeveloperOS — an AI-powered personal operating system for developers.",
    )
    parser.add_argument("--version", action="version", version=f"DeveloperOS {__version__}")

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    for cmd_cls in COMMANDS:
        cmd = cmd_cls()
        sub = subparsers.add_parser(cmd.name, help=cmd.help, description=cmd.help)
        cmd.configure(sub)
        sub.set_defaults(_handler=cmd)
    return parser


def _make_output_console_safe() -> None:
    """Avoid UnicodeEncodeError when printing non-cp1252 content on a Windows console.

    Reconfigures real stdio streams to UTF-8 with replacement. Guarded: streams without
    ``reconfigure`` (e.g. a StringIO used in tests) are left untouched.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def main(argv: Optional[Sequence[str]] = None) -> int:
    _make_output_console_safe()
    # Load installed/opted-in plugins (registers extra commands/providers) before parsing.
    from devos import plugins
    plugins.ensure_loaded()

    parser = build_parser()
    args = parser.parse_args(argv)

    handler = getattr(args, "_handler", None)
    if handler is None:
        parser.print_help()
        return 0

    ws = Workspace.load()
    try:
        return handler.run(args, ws)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
