"""Tests for Object Monitor translation files."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


TRANSLATIONS = Path("custom_components/object_monitor/translations")


class TestTranslations(unittest.TestCase):
    """Test translation file structure."""

    def test_uk_translation_has_same_top_level_keys_as_en(self) -> None:
        """Ukrainian translation mirrors English top-level structure."""
        en = json.loads((TRANSLATIONS / "en.json").read_text(encoding="utf-8"))
        uk = json.loads((TRANSLATIONS / "uk.json").read_text(encoding="utf-8"))

        self.assertEqual(set(uk), set(en))
        self.assertEqual(set(uk["config"]), set(en["config"]))
        self.assertEqual(set(uk["options"]), set(en["options"]))
        self.assertEqual(set(uk["selector"]), set(en["selector"]))


if __name__ == "__main__":
    unittest.main()
