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
            config=MonitorConfig(
                monitoring_label="monitor_this",
                category_labels=("security", "power"),
                object_labels=("qirim", "hotel_kyiv"),
            ),
        )

    def test_ignores_entity_without_monitoring_label(self) -> None:
        """Entities without the configured monitoring label are ignored."""
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
            {"monitor_this", "qirim", "security", "wifi"},
        )

        self.assertTrue(labels.is_monitored)
        self.assertEqual(labels.object_label, "qirim")
        self.assertEqual(labels.category, "security")
        self.assertIsNone(labels.timeout_seconds)
        self.assertIsNone(labels.category_error)

    def test_resolves_timeout_label_seconds(self) -> None:
        """A timeout label can override the default timeout in seconds."""
        labels = self.resolver.resolve_from_labels(
            "sensor.router",
            {"monitor_this", "qirim", "timeout_20s"},
        )

        self.assertTrue(labels.is_monitored)
        self.assertEqual(labels.timeout_seconds, 20)

    def test_resolves_timeout_label_minutes(self) -> None:
        """A timeout label can override the default timeout in minutes."""
        labels = self.resolver.resolve_from_labels(
            "sensor.router",
            {"monitor_this", "qirim", "timeout_7m"},
        )

        self.assertTrue(labels.is_monitored)
        self.assertEqual(labels.timeout_seconds, 420)

    def test_resolves_timeout_label_hours(self) -> None:
        """A timeout label can override the default timeout in hours."""
        labels = self.resolver.resolve_from_labels(
            "sensor.router",
            {"monitor_this", "qirim", "timeout_1h"},
        )

        self.assertTrue(labels.is_monitored)
        self.assertEqual(labels.timeout_seconds, 3600)

    def test_rejects_multiple_timeout_labels(self) -> None:
        """Exactly one timeout override label may be present."""
        labels = self.resolver.resolve_from_labels(
            "sensor.router",
            {"monitor_this", "qirim", "timeout_20s", "timeout_7m"},
        )

        self.assertEqual(labels.status, LabelResolutionStatus.MULTIPLE_TIMEOUTS)
        self.assertFalse(labels.is_monitored)
        self.assertIn("timeout_20s", labels.reason)
        self.assertIn("timeout_7m", labels.reason)

    def test_requires_configured_object_label(self) -> None:
        """Unknown labels are not treated as object labels."""
        labels = self.resolver.resolve_from_labels(
            "sensor.router",
            {"monitor_this", "critical", "wifi"},
        )

        self.assertEqual(labels.status, LabelResolutionStatus.MISSING_OBJECT)
        self.assertFalse(labels.is_monitored)

    def test_rejects_multiple_object_labels(self) -> None:
        """Exactly one configured object label must be present."""
        labels = self.resolver.resolve_from_labels(
            "sensor.router",
            {"monitor_this", "qirim", "hotel_kyiv"},
        )

        self.assertEqual(labels.status, LabelResolutionStatus.MULTIPLE_OBJECTS)
        self.assertFalse(labels.is_monitored)
        self.assertIn("hotel_kyiv", labels.reason)
        self.assertIn("qirim", labels.reason)

    def test_multiple_categories_keep_monitoring_with_category_error(self) -> None:
        """Category ambiguity does not disable monitoring itself."""
        labels = self.resolver.resolve_from_labels(
            "sensor.router",
            {"monitor_this", "qirim", "security", "power"},
        )

        self.assertTrue(labels.is_monitored)
        self.assertEqual(labels.object_label, "qirim")
        self.assertIsNone(labels.category)
        self.assertEqual(labels.category_error, "multiple_category_labels")

    def test_device_monitoring_is_not_special_when_custom_label_is_configured(
        self,
    ) -> None:
        """The default monitoring label is not hard-coded into resolution."""
        labels = self.resolver.resolve_from_labels(
            "sensor.router",
            {"device_monitoring", "qirim", "security"},
        )

        self.assertEqual(labels.status, LabelResolutionStatus.NOT_MONITORED)


if __name__ == "__main__":
    unittest.main()
