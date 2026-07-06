"""Tests for Object Monitor label resolution."""

from __future__ import annotations

import unittest

from module_loader import import_object_monitor_module

label_resolver_module = import_object_monitor_module("label_resolver")
models_module = import_object_monitor_module("models")

LabelResolver = label_resolver_module.LabelResolver
LabelResolutionStatus = models_module.LabelResolutionStatus
MonitorConfig = models_module.MonitorConfig


class TestLabelResolver(unittest.TestCase):
    """Test pure label resolution behavior."""

    def setUp(self) -> None:
        """Create a resolver with configured object labels."""
        self.resolver = LabelResolver(
            hass=None,
            config=MonitorConfig(object_labels=("qirim", "hotel_kyiv")),
        )

    def test_ignores_entity_without_monitoring_label(self) -> None:
        """Entities without device_monitoring are ignored."""
        labels = self.resolver.resolve_from_labels(
            "sensor.router",
            {"qirim", "security"},
        )

        self.assertEqual(labels.status, LabelResolutionStatus.NOT_MONITORED)
        self.assertFalse(labels.is_monitored)

    def test_resolves_object_and_category(self) -> None:
        """A valid monitored entity resolves object and category."""
        labels = self.resolver.resolve_from_labels(
            "sensor.router",
            {"device_monitoring", "qirim", "security", "wifi"},
        )

        self.assertTrue(labels.is_monitored)
        self.assertEqual(labels.object_label, "qirim")
        self.assertEqual(labels.category, "security")
        self.assertIsNone(labels.category_error)

    def test_requires_configured_object_label(self) -> None:
        """Unknown labels are not treated as object labels."""
        labels = self.resolver.resolve_from_labels(
            "sensor.router",
            {"device_monitoring", "critical", "wifi"},
        )

        self.assertEqual(labels.status, LabelResolutionStatus.MISSING_OBJECT)
        self.assertFalse(labels.is_monitored)

    def test_rejects_multiple_object_labels(self) -> None:
        """Exactly one configured object label must be present."""
        labels = self.resolver.resolve_from_labels(
            "sensor.router",
            {"device_monitoring", "qirim", "hotel_kyiv"},
        )

        self.assertEqual(labels.status, LabelResolutionStatus.MULTIPLE_OBJECTS)
        self.assertFalse(labels.is_monitored)
        self.assertIn("hotel_kyiv", labels.reason)
        self.assertIn("qirim", labels.reason)

    def test_multiple_categories_keep_monitoring_with_category_error(self) -> None:
        """Category ambiguity does not disable monitoring itself."""
        labels = self.resolver.resolve_from_labels(
            "sensor.router",
            {"device_monitoring", "qirim", "security", "light"},
        )

        self.assertTrue(labels.is_monitored)
        self.assertEqual(labels.object_label, "qirim")
        self.assertIsNone(labels.category)
        self.assertEqual(labels.category_error, "multiple_category_labels")


if __name__ == "__main__":
    unittest.main()
