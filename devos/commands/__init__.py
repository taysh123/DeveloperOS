"""CLI commands. Importing this package registers all built-in commands."""
from devos.commands.base import COMMANDS, Command, register

# Import command modules for their registration side effects.
from devos.commands import init_cmd as _init_cmd  # noqa: F401
from devos.commands import status_cmd as _status_cmd  # noqa: F401

__all__ = ["COMMANDS", "Command", "register"]
