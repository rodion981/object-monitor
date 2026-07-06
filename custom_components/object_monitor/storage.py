"""Persistent storage for the Object Monitor integration."""

from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_MINOR_VERSION, STORAGE_VERSION
from .models import MonitoredEntity, StoredEntityState, StoredMonitorState

_LOGGER = logging.getLogger(__name__)


class ObjectMonitorStore:
    """Persist Object Monitor state across Home Assistant restarts."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize storage for one config entry."""
        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY}.{entry_id}",
            minor_version=STORAGE_MINOR_VERSION,
        )
        self._state = StoredMonitorState()
        self._loaded = False

    @property
    def state(self) -> StoredMonitorState:
        """Return a snapshot of the currently loaded state."""
        return StoredMonitorState(entities=deepcopy(self._state.entities))

    @property
    def entities(self) -> dict[str, StoredEntityState]:
        """Return a snapshot of stored entity states."""
        return deepcopy(self._state.entities)

    async def async_load(self) -> StoredMonitorState:
        """Load persisted monitor state."""
        raw_state = await self._store.async_load()

        try:
            self._state = StoredMonitorState.from_json(raw_state)
        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.warning(
                "Ignoring invalid Object Monitor storage data: %s",
                err,
            )
            self._state = StoredMonitorState()

        self._loaded = True
        return self.state

    async def async_save_state(self, state: StoredMonitorState) -> None:
        """Persist the full monitor state."""
        self._ensure_loaded()
        self._state = StoredMonitorState(entities=deepcopy(state.entities))
        await self._async_save()

    async def async_save_entity(self, entity: MonitoredEntity) -> None:
        """Persist one monitored entity state."""
        self._ensure_loaded()
        stored_entity = StoredEntityState.from_monitored_entity(entity)
        self._state.entities[stored_entity.entity_id] = stored_entity
        await self._async_save()

    async def async_save_entities(self, entities: Iterable[MonitoredEntity]) -> None:
        """Persist several monitored entity states in one write."""
        self._ensure_loaded()
        for entity in entities:
            stored_entity = StoredEntityState.from_monitored_entity(entity)
            self._state.entities[stored_entity.entity_id] = stored_entity
        await self._async_save()

    async def async_remove_entity(self, entity_id: str) -> None:
        """Remove one entity from persisted state."""
        self._ensure_loaded()
        if entity_id not in self._state.entities:
            return

        self._state.entities.pop(entity_id)
        await self._async_save()

    async def async_remove_entities(self, entity_ids: Iterable[str]) -> None:
        """Remove several entities from persisted state in one write."""
        self._ensure_loaded()
        changed = False

        for entity_id in entity_ids:
            if entity_id in self._state.entities:
                self._state.entities.pop(entity_id)
                changed = True

        if changed:
            await self._async_save()

    async def async_clear(self) -> None:
        """Clear all persisted monitor state."""
        self._ensure_loaded()
        self._state = StoredMonitorState()
        await self._async_save()

    async def async_prune_except(self, active_entity_ids: Iterable[str]) -> None:
        """Remove stored entities that are no longer active monitor candidates."""
        self._ensure_loaded()
        active = set(active_entity_ids)
        stale_entity_ids = [
            entity_id
            for entity_id in self._state.entities
            if entity_id not in active
        ]

        if not stale_entity_ids:
            return

        for entity_id in stale_entity_ids:
            self._state.entities.pop(entity_id)

        await self._async_save()

    async def _async_save(self) -> None:
        """Write current state to Home Assistant storage."""
        await self._store.async_save(self._state.to_json())

    def _ensure_loaded(self) -> None:
        """Ensure storage was loaded before writes."""
        if not self._loaded:
            raise RuntimeError("Object Monitor storage must be loaded before use")
