import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app.config as config


class ConfigTests(unittest.TestCase):
    def setUp(self):
        config._DOTENV_CACHE = None
        config._SECRETS_CACHE = None

    def tearDown(self):
        config._DOTENV_CACHE = None
        config._SECRETS_CACHE = None

    def test_dotenv_is_loaded_for_offline_settings(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, ".env").write_text(
                '\n'.join(
                    [
                        'STORAGE_BACKEND="local"',
                        'OFFLINE_MODE="true"',
                        'LOCAL_STORAGE_ROOT=".local_data/storage"',
                        'GOOGLE_CALENDAR_SYNC_ENABLED="false"',
                    ]
                ),
                encoding="utf-8",
            )

            with patch("os.getcwd", return_value=root), patch.dict(os.environ, {}, clear=True):
                self.assertEqual(config.get_storage_backend(), "local")
                self.assertTrue(config.offline_mode())
                self.assertEqual(config.get_local_storage_root(), ".local_data/storage")
                self.assertFalse(config.google_calendar_sync_enabled())


if __name__ == "__main__":
    unittest.main()
