"""Tests for Object Monitor translation files."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


TRANSLATIONS = Path("custom_components/object_monitor/translations")


class TestTranslations(unittest.TestCase):
    """Test translation file structure."""

    def test_translations_have_same_keys_as_en(self) -> None:
        """All translations mirror English structure."""
        en = json.loads((TRANSLATIONS / "en.json").read_text(encoding="utf-8"))

        for path in sorted(TRANSLATIONS.glob("*.json")):
            if path.name == "en.json":
                continue

            with self.subTest(path=path.name):
                translated = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(_nested_keys(translated), _nested_keys(en))


def _nested_keys(value: object, prefix: str = "") -> set[str]:
    """Return all nested dictionary key paths."""
    if not isinstance(value, dict):
        return set()

    keys: set[str] = set()
    for key, nested_value in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        keys.add(path)
        keys.update(_nested_keys(nested_value, path))

    return keys


if __name__ == "__main__":
    unittest.main()
