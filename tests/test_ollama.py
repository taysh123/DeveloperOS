"""OllamaProvider tests — the first real (local, free) AI provider.

No network is ever touched: ``urllib.request.urlopen`` is patched. Verifies the
provider registers behind the existing seam, parses success responses, degrades
gracefully (labeled result, never raises), and respects env configuration.
"""
from __future__ import annotations

import io
import json
import os
import unittest
import urllib.error
from unittest import mock

from devos.providers.ai import available_providers, get_provider
from devos.providers.ollama import (DEFAULT_MODEL, DEFAULT_URL, OllamaProvider)


class _FakeResponse(io.BytesIO):
    """Minimal context-manager stand-in for urlopen's response object."""

    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def _ollama_reply(text: str) -> _FakeResponse:
    return _FakeResponse(json.dumps({
        "model": "llama3.2", "response": text, "eval_count": 42,
        "total_duration": 123456789,
    }).encode("utf-8"))


class TestRegistration(unittest.TestCase):
    def test_registered_behind_the_existing_seam(self) -> None:
        self.assertIn("ollama", available_providers())
        provider = get_provider("ollama")
        self.assertIsInstance(provider, OllamaProvider)
        self.assertEqual(provider.name, "ollama")

    def test_mock_is_still_the_default(self) -> None:
        prev = os.environ.pop("DEVOS_AI_PROVIDER", None)
        try:
            self.assertEqual(get_provider().name, "mock")
        finally:
            if prev is not None:
                os.environ["DEVOS_AI_PROVIDER"] = prev


class TestComplete(unittest.TestCase):
    def test_success_parses_text_and_meta(self) -> None:
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["payload"] = json.loads(req.data.decode("utf-8"))
            return _ollama_reply("The auth flow starts in src/auth.py.")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            res = OllamaProvider().complete(
                "How does auth work?", system="Ground your answer.", context="chunk text")

        self.assertEqual(res.provider, "ollama")
        self.assertTrue(res.meta["ok"])
        self.assertTrue(res.meta["local"])
        self.assertIn("auth flow", res.text)
        self.assertEqual(captured["url"], DEFAULT_URL + "/api/generate")
        self.assertEqual(captured["payload"]["system"], "Ground your answer.")
        self.assertIn("chunk text", captured["payload"]["prompt"])
        self.assertFalse(captured["payload"]["stream"])

    def test_connection_error_degrades_gracefully(self) -> None:
        err = urllib.error.URLError(ConnectionRefusedError(111, "refused"))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            res = OllamaProvider().complete("hello")
        self.assertEqual(res.provider, "ollama")
        self.assertFalse(res.meta["ok"])
        self.assertIn("OLLAMA UNAVAILABLE", res.text)
        self.assertIn("nothing left your machine", res.text)

    def test_bad_json_and_empty_response_degrade_gracefully(self) -> None:
        with mock.patch("urllib.request.urlopen",
                        return_value=_FakeResponse(b"not json")):
            res = OllamaProvider().complete("hello")
        self.assertFalse(res.meta["ok"])

        with mock.patch("urllib.request.urlopen",
                        return_value=_FakeResponse(b'{"response": ""}')):
            res2 = OllamaProvider().complete("hello")
        self.assertFalse(res2.meta["ok"])

    def test_never_raises_on_http_error(self) -> None:
        err = urllib.error.HTTPError("u", 404, "not found", {}, io.BytesIO(b""))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            res = OllamaProvider().complete("hello")
        self.assertFalse(res.meta["ok"])
        self.assertIn("HTTP 404", res.meta["error"])


class TestConfig(unittest.TestCase):
    def test_env_overrides(self) -> None:
        with mock.patch.dict(os.environ, {"DEVOS_OLLAMA_URL": "http://127.0.0.1:9999/",
                                          "DEVOS_OLLAMA_MODEL": "codellama"}):
            p = OllamaProvider()
        self.assertEqual(p.base_url, "http://127.0.0.1:9999")  # trailing slash stripped
        self.assertEqual(p.model, "codellama")

    def test_defaults(self) -> None:
        env = {k: v for k, v in os.environ.items()
               if k not in ("DEVOS_OLLAMA_URL", "DEVOS_OLLAMA_MODEL")}
        with mock.patch.dict(os.environ, env, clear=True):
            p = OllamaProvider()
        self.assertEqual(p.base_url, DEFAULT_URL)
        self.assertEqual(p.model, DEFAULT_MODEL)

    def test_ping_false_when_down(self) -> None:
        with mock.patch("urllib.request.urlopen",
                        side_effect=urllib.error.URLError("down")):
            self.assertFalse(OllamaProvider().ping())


if __name__ == "__main__":
    unittest.main()
