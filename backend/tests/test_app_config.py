from __future__ import annotations

import sys
from pathlib import Path
import unittest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import application as main  # noqa: E402


class AppConfigTests(unittest.TestCase):
    def test_parse_cors_origins_uses_comma_separated_environment_value(self) -> None:
        self.assertEqual(
            main._parse_cors_origins("http://localhost:3000, http://localhost:5173"),
            ["http://localhost:3000", "http://localhost:5173"],
        )

    def test_parse_cors_origins_defaults_to_wildcard_for_empty_value(self) -> None:
        self.assertEqual(main._parse_cors_origins(""), ["*"])
        self.assertEqual(main._parse_cors_origins(None), ["*"])


if __name__ == "__main__":
    unittest.main()
