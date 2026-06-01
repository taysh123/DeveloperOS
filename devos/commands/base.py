"""Command base class and registry for the CLI.

Each command subclasses :class:`Command`, declares a ``name``/``help``, optionally
adds arguments, and implements :meth:`run`. Commands register themselves with the
``@register`` decorator; ``devos.commands`` imports the modules to populate the list.
"""
from __future__ import annotations

import argparse
from typing import List, Type

from devos.core.workspace import Workspace


class Command:
    name: str = ""
    help: str = ""

    def configure(self, parser: argparse.ArgumentParser) -> None:
        """Add command-specific arguments. Override as needed."""

    def run(self, args: argparse.Namespace, ws: Workspace) -> int:
        """Execute the command. Return a process exit code (0 == success)."""
        raise NotImplementedError


COMMANDS: List[Type[Command]] = []


def register(cls: Type[Command]) -> Type[Command]:
    COMMANDS.append(cls)
    return cls
