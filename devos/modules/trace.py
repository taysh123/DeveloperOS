"""Pluggable parsing of errors / stack traces / logs into structured frames.

Pure (no DB, no IO). Add a language by writing a parser ``(text) -> ParsedTrace | None``
and registering it in ``TRACE_PARSERS``; the first parser that yields frames wins,
otherwise a generic path:line scan is used. See docs/ROADMAP.md Phase 5.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Frame:
    file: str
    line: int | None
    func: str | None
    raw: str


@dataclass
class ParsedTrace:
    error_type: str | None = None
    error_message: str | None = None
    frames: list[Frame] = field(default_factory=list)
    language: str | None = None
    raw: str = ""


_PY_FRAME = re.compile(r'^\s*File "(?P<file>.+?)", line (?P<line>\d+)(?:, in (?P<func>.+))?\s*$')
_PY_ERROR = re.compile(r'^(?P<type>[A-Za-z_][\w.]*(?:Error|Exception|Warning|Interrupt|Exit))'
                       r'(?::\s*(?P<msg>.*))?\s*$')
_NODE_FRAME = re.compile(r'^\s*at (?:(?P<func>.+?) \()?(?P<file>[^()\s]+?):(?P<line>\d+)'
                         r'(?::\d+)?\)?\s*$')
_NODE_ERROR = re.compile(r'^(?P<type>[A-Za-z_]\w*(?:Error|Exception|Warning))'
                         r'(?::\s*(?P<msg>.*))?\s*$')
_GENERIC = re.compile(r'(?P<file>[\w./\\-]+\.[A-Za-z0-9]+):(?P<line>\d+)')


def parse_python(text: str) -> ParsedTrace | None:
    if 'Traceback (most recent call last)' not in text and 'File "' not in text:
        return None
    frames = []
    error_type = error_message = None
    for line in text.splitlines():
        m = _PY_FRAME.match(line)
        if m:
            frames.append(Frame(file=m.group("file"), line=int(m.group("line")),
                                func=(m.group("func") or None), raw=line.strip()))
            continue
        e = _PY_ERROR.match(line.strip())
        if e:
            error_type = e.group("type")
            error_message = (e.group("msg") or "").strip() or None
    if not frames:
        return None
    return ParsedTrace(error_type, error_message, frames, "python", text)


def parse_node(text: str) -> ParsedTrace | None:
    if "\n    at " not in text and not text.lstrip().startswith("at "):
        return None
    frames = []
    for line in text.splitlines():
        m = _NODE_FRAME.match(line)
        if m:
            frames.append(Frame(file=m.group("file"), line=int(m.group("line")),
                                func=(m.group("func") or None), raw=line.strip()))
    if not frames:
        return None
    error_type = error_message = None
    for line in text.splitlines():
        e = _NODE_ERROR.match(line.strip())
        if e:
            error_type = e.group("type")
            error_message = (e.group("msg") or "").strip() or None
            break
    return ParsedTrace(error_type, error_message, frames, "node", text)


def parse_generic(text: str) -> ParsedTrace:
    frames = [Frame(file=m.group("file").replace("\\", "/"), line=int(m.group("line")),
                    func=None, raw=m.group(0))
              for m in _GENERIC.finditer(text)]
    first = next((ln.strip() for ln in text.splitlines() if ln.strip()), None)
    return ParsedTrace(error_type=None, error_message=first, frames=frames,
                       language=None, raw=text)


TRACE_PARSERS = [parse_python, parse_node]


def parse_trace(text: str) -> ParsedTrace:
    """Parse a trace/log into structured frames. First language parser with frames wins."""
    for parser in TRACE_PARSERS:
        result = parser(text)
        if result and result.frames:
            return result
    return parse_generic(text)
