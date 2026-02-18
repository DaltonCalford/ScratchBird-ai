from __future__ import annotations

import os
import unittest

from scratchbird_ai.settings import RuntimeSettings, load_runtime_settings


class SettingsTests(unittest.TestCase):
    def test_runtime_settings_mode_normalization(self) -> None:
        settings = RuntimeSettings(adapter_mode="HYBRID")
        self.assertEqual(settings.normalized_mode(), "hybrid")

    def test_runtime_settings_invalid_mode_falls_back_to_mock(self) -> None:
        settings = RuntimeSettings(adapter_mode="invalid")
        self.assertEqual(settings.normalized_mode(), "mock")

    def test_load_runtime_settings_from_env(self) -> None:
        env = {
            "SCRATCHBIRD_AI_ADAPTER_MODE": "hybrid",
            "SCRATCHBIRD_AI_HTTP_BASE_URL": "http://localhost:9999",
            "SCRATCHBIRD_AI_HTTP_TIMEOUT_SEC": "3.5",
            "SCRATCHBIRD_AI_HTTP_DIALECTS": "native",
        }

        backup = {key: os.environ.get(key) for key in env}
        try:
            os.environ.update(env)
            settings = load_runtime_settings()
        finally:
            for key, value in backup.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.assertEqual(settings.normalized_mode(), "hybrid")
        self.assertEqual(settings.http_base_url, "http://localhost:9999")
        self.assertEqual(settings.http_timeout_sec, 3.5)
        self.assertEqual(settings.http_dialects, ("native",))


if __name__ == "__main__":
    unittest.main()
