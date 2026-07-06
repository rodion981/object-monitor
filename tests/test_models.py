"""Tests for Object Monitor data models."""

from __future__ import annotations

from datetime import datetime, timezone
import unittest

from module_loader import import_object_monitor_module

models_module = import_object_monitor_module("models")

MonitorConfig = models_module.MonitorConfig
MonitoredEntity = models_module.MonitoredEntity
NotificationEventType = models_module.NotificationEventType
SecurityStateEvent = models_module.SecurityStateEvent
SecuritySystemState = models_module.SecuritySystemState
StoredEntityState = models_module.StoredEntityState
StoredMonitorState = models_module.StoredMonitorState


class TestStoredModels(unittest.TestCase):
    """Test persistence model serialization."""

    def test_monitor_config_label_defaults(self) -> None:
        """Default label roles preserve existing integrations."""
        config = MonitorConfig()

        self.assertEqual(config.monitoring_label, "device_monitoring")
        self.assertEqual(config.category_labels, ("security", "light", "climate"))

    def test_monitor_config_display_names_fall_back_to_labels(self) -> None:
        """Configured display names override raw labels only for presentation."""
        config = MonitorConfig(
            object_names={"home": "Дім"},
            category_names={"power": "Живлення"},
        )

        self.assertEqual(config.object_display_name("home"), "Дім")
        self.assertEqual(config.object_display_name("restaurant"), "restaurant")
        self.assertEqual(config.category_display_name("power"), "Живлення")
        self.assertEqual(config.category_display_name("security"), "security")

    def test_security_state_event_serializes_for_event_bus(self) -> None:
        """Security state events expose provider-neutral event data."""
        notified_at = datetime(2026, 7, 6, 14, 52, tzinfo=timezone.utc)
        event = SecurityStateEvent(
            entity_id="alarm_control_panel.home",
            friendly_name="Security System",
            object_label="home",
            previous_state=SecuritySystemState.ARMED_AWAY,
            state=SecuritySystemState.TRIGGERED,
            notified_at=notified_at,
        )

        data = event.as_event_data()

        self.assertEqual(data["event_type"], "security_state")
        self.assertEqual(data["entity_id"], "alarm_control_panel.home")
        self.assertEqual(data["object_label"], "home")
        self.assertEqual(data["category"], "security")
        self.assertEqual(data["previous_state"], "armed_away")
        self.assertEqual(data["state"], "triggered")
        self.assertEqual(data["notified_at"], notified_at.isoformat())

    def test_stored_entity_round_trip(self) -> None:
        """Stored entity state survives JSON serialization."""
        unavailable_since = datetime(2026, 7, 6, 10, 0, tzinfo=timezone.utc)
        notified_at = datetime(2026, 7, 6, 10, 7, tzinfo=timezone.utc)

        entity = MonitoredEntity(
            entity_id="binary_sensor.router",
            object_label="qirim",
            category="security",
            friendly_name="Main Router",
            unavailable_since=unavailable_since,
            offline_confirmed=True,
            notified_offline=True,
            last_notification_type=NotificationEventType.OFFLINE,
            last_notified_at=notified_at,
        )

        stored = StoredEntityState.from_monitored_entity(entity)
        restored = StoredEntityState.from_json(stored.to_json())

        self.assertEqual(restored.entity_id, entity.entity_id)
        self.assertEqual(restored.object_label, entity.object_label)
        self.assertEqual(restored.category, entity.category)
        self.assertEqual(restored.friendly_name, entity.friendly_name)
        self.assertEqual(restored.unavailable_since, unavailable_since)
        self.assertTrue(restored.offline_confirmed)
        self.assertTrue(restored.notified_offline)
        self.assertEqual(restored.last_notification_type, NotificationEventType.OFFLINE)
        self.assertEqual(restored.last_notified_at, notified_at)

    def test_stored_monitor_state_ignores_empty_data(self) -> None:
        """Empty storage data creates an empty state."""
        state = StoredMonitorState.from_json(None)

        self.assertEqual(state.entities, {})


if __name__ == "__main__":
    unittest.main()
