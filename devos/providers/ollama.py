"""Ollama provider — the first *real* AI backend, local-first and free.

Talks to an Ollama daemon on the user's own machine (default ``http://127.0.0.1:11434``)
using only the stdlib (``urllib``), preserving the zero-runtime-dependency rule.
Nothing ever leaves the machine and no API key exists — this matches the project's
privacy/cost stance (FUTURE_ROADMAP §3: "Ollama first for the privacy story").

Design rules:
- **Never crash the pipeline.** If the daemon is unreachable, times out, or returns
  garbage, ``complete`` returns a clearly-labeled, honest error ``AIResult`` (with
  ``meta["ok"] = False``) instead of raising — the same graceful spirit as the
  settings fallback (D-0022). Callers keep working; the user sees what happened
  and how to fix it.
- **The prompt is data.** We pass the grounding system prompt through unchanged;
  the provider adds no instructions of its own (SECURITY §5).
- **Configuration via environment only** (no secrets exist, but the same channel
  keeps it consistent): ``DEVOS_OLLAMA_URL`` and ``DEVOS_OLLAMA_MODEL``.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from devos.providers.ai import AIProvider, AIResult, register_provider

DEFAULT_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3.2"
DEFAULT_TIMEOUT = 120.0  # local models can be slow on first load

UNAVAILABLE_TEMPLATE = (
    "[OLLAMA UNAVAILABLE] Could not reach the local Ollama server at {url} ({reason}).\n"
    "DeveloperOS made no external calls and nothing left your machine.\n"
    "To use local AI: install Ollama (https://ollama.com), run `ollama pull {model}`, "
    "make sure the app is running, then try again — or switch back to the Offline "
    "provider in Settings."
)


class OllamaProvider(AIProvider):
    """Local models served by Ollama. Free, private, no key."""

    name = "ollama"

    def __init__(self, *, base_url: str | None = None, model: str | None = None,
                 timeout: float = DEFAULT_TIMEOUT) -> None:
        self.base_url = (base_url or os.environ.get("DEVOS_OLLAMA_URL")
                         or DEFAULT_URL).rstrip("/")
        self.model = model or os.environ.get("DEVOS_OLLAMA_MODEL") or DEFAULT_MODEL
        self.timeout = timeout

    # -- health -----------------------------------------------------------
    def ping(self, *, timeout: float = 2.0) -> bool:
        """True if the local daemon answers. Cheap; used for status surfacing."""
        try:
            with urllib.request.urlopen(self.base_url + "/api/version",
                                        timeout=timeout) as resp:
                return resp.status == 200
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return False

    # -- completion ---------------------------------------------------------
    def complete(self, prompt: str, *, system: str | None = None,
                 context: str | None = None) -> AIResult:
        full_prompt = prompt if not context else f"{prompt}\n\nContext:\n{context}"
        payload: dict = {"model": self.model, "prompt": full_prompt, "stream": False}
        if system:
            payload["system"] = system

        request = urllib.request.Request(
            self.base_url + "/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return self._unavailable(f"HTTP {exc.code}")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return self._unavailable(getattr(exc, "reason", None) or str(exc) or "connection error")
        except (json.JSONDecodeError, ValueError):
            return self._unavailable("invalid response from server")

        text = (data.get("response") or "").strip() if isinstance(data, dict) else ""
        if not text:
            return self._unavailable("empty response from model")
        return AIResult(
            text=text,
            provider=self.name,
            meta={
                "ok": True,
                "model": data.get("model", self.model),
                "local": True,
                "eval_count": data.get("eval_count"),
                "total_duration_ns": data.get("total_duration"),
            },
        )

    def _unavailable(self, reason) -> AIResult:
        return AIResult(
            text=UNAVAILABLE_TEMPLATE.format(url=self.base_url, reason=reason,
                                             model=self.model),
            provider=self.name,
            meta={"ok": False, "error": str(reason), "local": True},
        )


# Register on import so settings/`available_providers()` see it (same seam plugins use).
register_provider(OllamaProvider.name, OllamaProvider)
