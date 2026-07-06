"""Tests for Object Monitor data models."""

from __future__ import annotations

from datetime import datetime, timezone
import unittest

from module_loader import import_object_monitor_module

models_module = import_object_monitor_module("models")

MonitoredEntity = models_module.MonitoredEntity
NotificationEventType = models_module.NotificationEventType
StoredEntityState = models_module.StoredEntityState
StoredMonitorState = models_module.StoredMonitorState


class TestStoredModels(unittest.TestCase):
    """Test persistence model serialization."""

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
