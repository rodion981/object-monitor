"""Security system state monitoring for the Object Monitor integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any

from homeassistant.const import (
    ATTR_ENTITY_ID as HA_ATTR_ENTITY_ID,
    EVENT_STATE_CHANGED,
)
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, State, callback
from homeassistant.helpers import entity_registry as er

from .const import (
    ALARM_CONTROL_PANEL_DOMAIN,
    CATEGORY_SECURITY,
    EVENT_ENTITY_REGISTRY_UPDATED,
    EVENT_OBJECT_MONITOR,
    SECURITY_SYSTEM_LABEL,
)
from .models import MonitorConfig, SecurityStateEvent, SecuritySystemState
from .notification_manager import NotificationManager

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class SecurityEntity:
    """Resolved security monitoring metadata for one entity."""

    entity_id: str
    object_label: str


class SecurityMonitor:
    """Monitor security system state changes."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: MonitorConfig,
        notification_manager: NotificationManager,
    ) -> None:
        """Initialize the security monitor."""
        self._hass = hass
        self._config = config
        self._notification_manager = notification_manager
        self._last_states: dict[str, SecuritySystemState] = {}
        self._unsubscribers: list[CALLBACK_TYPE] = []
        self._started = False

    @property
    def tracked_count(self) -> int:
        """Return the number of security entities with remembered state."""
        return len(self._last_states)

    async def async_start(self) -> None:
        """Start security monitoring and build the initial state baseline."""
        if self._started:
            return

        self._started = True
        self._unsubscribers.append(
            self._hass.bus.async_listen(
                EVENT_STATE_CHANGED,
                self._handle_state_changed_event,
            )
        )
        self._unsubscribers.append(
            self._hass.bus.async_listen(
                EVENT_ENTITY_REGISTRY_UPDATED,
                self._handle_entity_registry_updated_event,
            )
        )

        await self.async_reconcile()

    async def async_stop(self) -> None:
        """Stop security monitoring."""
        if not self._started:
            return

        self._started = False
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        self._last_states.clear()

    async def async_reconcile(self) -> None:
        """Rebuild current security entity baseline without notifications."""
        registry = er.async_get(self._hass)
        active_entity_ids: set[str] = set()

        for entity_id, entry in registry.entities.items():
            entity = self._resolve_entity(entity_id, entry)
            if entity is None:
                continue

            state = _security_state(self._hass.states.get(entity_id))
            if state is None:
                continue

            active_entity_ids.add(entity_id)
            self._last_states[entity_id] = state

        for stale_entity_id in set(self._last_states) - active_entity_ids:
            self._last_states.pop(stale_entity_id, None)

    @callback
    def _handle_state_changed_event(self, event: Event) -> None:
        """Handle Home Assistant state_changed events."""
        entity_id = event.data.get(HA_ATTR_ENTITY_ID)
        if not isinstance(entity_id, str):
            return

        if not entity_id.startswith(f"{ALARM_CONTROL_PANEL_DOMAIN}."):
            return

        self._hass.async_create_task(self._async_process_state_change(event))

    async def _async_process_state_change(self, event: Event) -> None:
        """Process one security system state change."""
        entity_id = event.data.get(HA_ATTR_ENTITY_ID)
        if not isinstance(entity_id, str):
            return

        entity = self._resolve_entity_id(entity_id)
        if entity is None:
            self._last_states.pop(entity_id, None)
            return

        new_state = event.data.get("new_state")
        security_state = _security_state(new_state)
        if security_state is None:
            self._last_states.pop(entity_id, None)
            return

        previous_state = self._last_states.get(entity_id)
        if previous_state == security_state:
            return

        self._last_states[entity_id] = security_state

        if previous_state is None:
            return

        event_payload = SecurityStateEvent(
            entity_id=entity.entity_id,
            friendly_name=_friendly_name(self._hass, entity.entity_id, new_state),
            object_label=entity.object_label,
            previous_state=previous_state,
            state=security_state,
            category=CATEGORY_SECURITY,
            notified_at=_utcnow(),
        )
        self._hass.bus.async_fire(EVENT_OBJECT_MONITOR, event_payload.as_event_data())
        await self._notification_manager.async_notify(event_payload)

    @callback
    def _handle_entity_registry_updated_event(self, event: Event) -> None:
        """Handle entity registry updates that may change security labels."""
        entity_id = event.data.get(HA_ATTR_ENTITY_ID)

        if isinstance(entity_id, str):
            self._hass.async_create_task(self._async_reconcile_entity(entity_id))
            return

        self._hass.async_create_task(self.async_reconcile())

    async def _async_reconcile_entity(self, entity_id: str) -> None:
        """Reconcile one security entity after registry metadata changes."""
        entity = self._resolve_entity_id(entity_id)
        state = _security_state(self._hass.states.get(entity_id))
        if entity is None or state is None:
            self._last_states.pop(entity_id, None)
            return

        self._last_states[entity_id] = state

    def _resolve_entity_id(self, entity_id: str) -> SecurityEntity | None:
        """Resolve security metadata for one entity ID."""
        registry = er.async_get(self._hass)
        entry = registry.async_get(entity_id)
        if entry is None:
            return None

        return self._resolve_entity(entity_id, entry)

    def _resolve_entity(self, entity_id: str, entry: Any) -> SecurityEntity | None:
        """Resolve security metadata from an entity registry entry."""
        if not entity_id.startswith(f"{ALARM_CONTROL_PANEL_DOMAIN}."):
            return None

        labels = _entry_labels(entry)
        if SECURITY_SYSTEM_LABEL not in labels:
            return None

        object_matches = sorted(labels & self._config.object_label_set)
        if not object_matches:
            _LOGGER.warning(
                "Skipping security system entity %s: missing_object_label",
                entity_id,
            )
            return None

        if len(object_matches) > 1:
            _LOGGER.warning(
                "Skipping security system entity %s: multiple_object_labels: %s",
                entity_id,
                ", ".join(object_matches),
            )
            return None

        return SecurityEntity(entity_id=entity_id, object_label=object_matches[0])


def _entry_labels(entry: Any) -> frozenset[str]:
    """Return normalized labels from an entity registry entry."""
    raw_labels = getattr(entry, "labels", set())
    return frozenset(label.strip().lower() for label in raw_labels if label.strip())


def _security_state(state: Any) -> SecuritySystemState | None:
    """Return a supported security system state from a Home Assistant state."""
    if not isinstance(state, State):
        return None

    try:
        return SecuritySystemState(state.state)
    except ValueError:
        return None


def _friendly_name(hass: HomeAssistant, entity_id: str, state: Any) -> str:
    """Return a user-facing entity name."""
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    if entry is not None:
        for attribute in ("name", "name_by_user"):
            value = getattr(entry, attribute, None)
            if value:
                return str(value)

    if not isinstance(state, State):
        return entity_id

    return str(state.attributes.get("friendly_name") or entity_id)


def _utcnow() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)
