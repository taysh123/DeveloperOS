"""CLI commands. Importing this package registers all built-in commands."""
from devos.commands.base import COMMANDS, Command, register

# Import command modules for their registration side effects.
from devos.commands import init_cmd as _init_cmd  # noqa: F401
from devos.commands import status_cmd as _status_cmd  # noqa: F401
from devos.commands import scan_cmd as _scan_cmd  # noqa: F401
from devos.commands import projects_cmd as _projects_cmd  # noqa: F401
from devos.commands import index_cmd as _index_cmd  # noqa: F401
from devos.commands import search_cmd as _search_cmd  # noqa: F401
from devos.commands import ask_cmd as _ask_cmd  # noqa: F401
from devos.commands import explain_cmd as _explain_cmd  # noqa: F401
from devos.commands import debug_cmd as _debug_cmd  # noqa: F401

__all__ = ["COMMANDS", "Command", "register"]
