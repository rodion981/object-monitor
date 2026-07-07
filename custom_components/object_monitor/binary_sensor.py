"""Binary sensors for the Object Monitor integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ObjectMonitorConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ObjectMonitorConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Object Monitor binary sensors for one config entry."""
    runtime = entry.runtime_data
    entities = [
        ObjectProblemBinarySensor(entry, object_label)
        for object_label in runtime.config.object_labels
    ]
    async_add_entities(entities)


class ObjectProblemBinarySensor(BinarySensorEntity):
    """Expose whether an object has at least one confirmed offline entity."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_should_poll = False

    def __init__(
        self,
        entry: ObjectMonitorConfigEntry,
        object_label: str,
    ) -> None:
        """Initialize an object problem binary sensor."""
        self._entry = entry
        self._object_label = object_label
        self._attr_unique_id = (
            f"{entry.entry_id}_{object_label}_availability_problem"
        )
        self._attr_suggested_object_id = f"{object_label}_availability_problem"
        self._attr_translation_key = "object_availability_problem"
        self._attr_has_entity_name = True
        self._attr_translation_placeholders = {
            "object": entry.runtime_data.config.object_display_name(object_label),
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to runtime aggregate availability updates."""
        self.async_on_remove(
            self._entry.runtime_data.async_add_object_status_listener(
                self._handle_object_status_updated,
            )
        )

    @property
    def is_on(self) -> bool:
        """Return true when the object has at least one availability problem."""
        return self._offline_count > 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return object availability aggregate attributes."""
        offline_entities = self._offline_entities
        pending_entities = self._pending_entities

        return {
            "object_label": self._object_label,
            "object_name": self._object_name,
            "monitored_count": self._monitored_count,
            "offline_count": len(offline_entities),
            "pending_count": len(pending_entities),
            "offline_entities": offline_entities,
            "pending_entities": pending_entities,
        }

    @property
    def _object_name(self) -> str:
        """Return the configured display name for this object."""
        return self._entry.runtime_data.config.object_display_name(self._object_label)

    @property
    def _monitored_count(self) -> int:
        """Return the number of availability-monitored entities for this object."""
        monitored = self._entry.runtime_data.label_resolver.resolve_all_monitored()
        return sum(
            1
            for labels in monitored.values()
            if labels.object_label == self._object_label
        )

    @property
    def _offline_entities(self) -> list[str]:
        """Return confirmed offline availability entities for this object."""
        tracker = self._entry.runtime_data.tracker
        if tracker is None:
            return []

        return sorted(
            entity.entity_id
            for entity in tracker.entities.values()
            if entity.object_label == self._object_label and entity.is_offline
        )

    @property
    def _pending_entities(self) -> list[str]:
        """Return pending availability entities for this object."""
        tracker = self._entry.runtime_data.tracker
        if tracker is None:
            return []

        return sorted(
            entity.entity_id
            for entity in tracker.entities.values()
            if entity.object_label == self._object_label and entity.is_pending
        )

    @property
    def _offline_count(self) -> int:
        """Return the number of confirmed offline entities for this object."""
        return len(self._offline_entities)

    @callback
    def _handle_object_status_updated(self) -> None:
        """Handle an aggregate object status update."""
        self.async_write_ha_state()
