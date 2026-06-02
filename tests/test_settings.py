"""Dashboard slice 5 — settings store + provider resolution tests (TDD)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from devos import settings


class TestSettingsStore(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._dir.name)
        self.addCleanup(self._dir.cleanup)

    def test_defaults_when_no_file(self) -> None:
        s = settings.load(self.data_dir)
        self.assertTrue(s.ai_enabled)
        self.assertEqual(s.ai_provider, "mock")

    def test_save_then_reload_roundtrip(self) -> None:
        settings.save(self.data_dir, ai_enabled=False, ai_provider="ollama")
        s = settings.load(self.data_dir)
        self.assertFalse(s.ai_enabled)
        self.assertEqual(s.ai_provider, "ollama")

    def test_partial_save_keeps_other_field(self) -> None:
        settings.save(self.data_dir, ai_provider="claude")
        settings.save(self.data_dir, ai_enabled=False)
        s = settings.load(self.data_dir)
        self.assertFalse(s.ai_enabled)
        self.assertEqual(s.ai_provider, "claude")  # provider preserved across a partial save

    def test_invalid_provider_rejected(self) -> None:
        with self.assertRaises(ValueError):
            settings.save(self.data_dir, ai_provider="not-a-provider")

    def test_corrupt_file_falls_back_to_defaults(self) -> None:
        (self.data_dir / settings.SETTINGS_FILENAME).write_text("{ not json", encoding="utf-8")
        s = settings.load(self.data_dir)
        self.assertTrue(s.ai_enabled)
        self.assertEqual(s.ai_provider, "mock")

    def test_unknown_provider_in_file_falls_back(self) -> None:
        (self.data_dir / settings.SETTINGS_FILENAME).write_text(
            json.dumps({"ai_provider": "ghost", "ai_enabled": True}), encoding="utf-8")
        self.assertEqual(settings.load(self.data_dir).ai_provider, "mock")

    def test_saved_file_never_contains_secret_keys(self) -> None:
        # save() only accepts the two non-secret fields; even if a caller tried to smuggle a
        # key it cannot reach disk. Verify the on-disk file is exactly the whitelist.
        settings.save(self.data_dir, ai_provider="claude")
        raw = json.loads((self.data_dir / settings.SETTINGS_FILENAME).read_text(encoding="utf-8"))
        self.assertEqual(set(raw.keys()), {"ai_enabled", "ai_provider"})
        self.assertNotIn("api_key", raw)

    def test_save_signature_rejects_arbitrary_kwargs(self) -> None:
        with self.assertRaises(TypeError):
            settings.save(self.data_dir, api_key="sk-secret")  # not an accepted parameter


class TestProviderResolution(unittest.TestCase):
    def test_disabled_resolves_to_mock(self) -> None:
        self.assertEqual(settings.effective_provider_name("claude", False), "mock")

    def test_unavailable_preferred_resolves_to_mock(self) -> None:
        # claude is in the catalog but not registered in providers.ai yet → safe fallback
        self.assertEqual(settings.effective_provider_name("claude", True), "mock")

    def test_available_preferred_is_used(self) -> None:
        self.assertEqual(settings.effective_provider_name("mock", True), "mock")

    def test_catalog_has_four_known_providers(self) -> None:
        ids = [p["id"] for p in settings.PROVIDERS]
        self.assertEqual(ids, ["mock", "ollama", "claude", "openai"])

    def test_key_present_reads_env_as_boolean(self) -> None:
        prev = os.environ.get("ANTHROPIC_API_KEY")
        try:
            os.environ["ANTHROPIC_API_KEY"] = "sk-test"
            self.assertIs(settings.key_present("claude"), True)
            os.environ.pop("ANTHROPIC_API_KEY", None)
            self.assertIs(settings.key_present("claude"), False)
        finally:
            if prev is None:
                os.environ.pop("ANTHROPIC_API_KEY", None)
            else:
                os.environ["ANTHROPIC_API_KEY"] = prev

    def test_key_present_false_for_local_provider(self) -> None:
        self.assertIs(settings.key_present("mock"), False)
        self.assertIs(settings.key_present("ollama"), False)


if __name__ == "__main__":
    unittest.main()
