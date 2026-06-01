"""AI provider abstraction.

A real Claude provider will be added later behind :class:`AIProvider` (see
docs/DECISIONS.md D-0003). Until then :class:`MockAIProvider` returns deterministic,
clearly-labeled stub output so the whole pipeline is testable offline with no API key.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AIResult:
    """Result of an AI completion."""

    text: str
    provider: str
    meta: dict[str, Any] = field(default_factory=dict)


class AIProvider(ABC):
    """Interface every AI backend must implement."""

    name: str = "base"

    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        context: str | None = None,
    ) -> AIResult:
        """Return a completion for ``prompt`` given optional ``system``/``context``."""
        raise NotImplementedError


class MockAIProvider(AIProvider):
    """Offline, deterministic provider used until a real model is wired in."""

    name = "mock"

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        context: str | None = None,
    ) -> AIResult:
        lines = ["[MOCK AI] No real model is configured yet (see docs/DECISIONS.md D-0003)."]
        if system:
            lines.append(f"system: {system}")
        if context:
            preview = context if len(context) <= 500 else context[:500] + "..."
            lines.append(f"context ({len(context)} chars): {preview}")
        lines.append(f"prompt: {prompt}")
        return AIResult(
            text="\n".join(lines),
            provider=self.name,
            meta={"mock": True, "prompt_chars": len(prompt)},
        )


_REGISTRY: dict[str, type[AIProvider]] = {"mock": MockAIProvider}


def register_provider(name: str, cls: type[AIProvider]) -> None:
    """Register an AI provider implementation (used by plugins; see devos/plugins.py)."""
    _REGISTRY[name] = cls


def available_providers() -> list[str]:
    return sorted(_REGISTRY)


def get_provider(name: str | None = None) -> AIProvider:
    """Return an AI provider instance.

    Selection order: explicit ``name`` → ``DEVOS_AI_PROVIDER`` env var → ``"mock"``.
    """
    selected = name or os.environ.get("DEVOS_AI_PROVIDER", "mock")
    try:
        return _REGISTRY[selected]()
    except KeyError:
        available = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown AI provider {selected!r}. Available: {available}.") from None
