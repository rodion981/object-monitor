"""Home Assistant event monitoring for the Object Monitor integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.const import (
    ATTR_ENTITY_ID as HA_ATTR_ENTITY_ID,
    EVENT_STATE_CHANGED,
)
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, State, callback

from .const import (
    EVENT_ENTITY_REGISTRY_UPDATED,
    EVENT_OBJECT_MONITOR,
    STATE_UNAVAILABLE,
)
from .entity_tracker import EntityTracker
from .label_resolver import LabelResolver
from .models import EntityLabels, LabelResolutionStatus, NotificationEvent

_LOGGER = logging.getLogger(__name__)


class ObjectMonitor:
    """Listen to Home Assistant state changes and drive entity tracking."""

    def __init__(
        self,
        hass: HomeAssistant,
        label_resolver: LabelResolver,
        tracker: EntityTracker,
    ) -> None:
        """Initialize the monitor."""
        self._hass = hass
        self._label_resolver = label_resolver
        self._tracker = tracker
        self._unsubscribers: list[CALLBACK_TYPE] = []
        self._started = False

    async def async_start(self) -> None:
        """Start monitoring and reconcile current Home Assistant state."""
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
        """Stop monitoring and cancel outstanding tracker timers."""
        if not self._started:
            return

        self._started = False
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        await self._tracker.async_shutdown()

    async def async_reconcile(self) -> None:
        """Reconcile registry labels, current states, and stored tracker state."""
        monitored = self._label_resolver.resolve_all_monitored()
        await self._tracker.async_prune_except(monitored)

        for entity_id, labels in monitored.items():
            state = self._hass.states.get(entity_id)
            if _is_unavailable_state(state):
                await self._tracker.async_mark_unavailable(
                    labels,
                    _friendly_name(entity_id, state),
                )
            else:
                await self._tracker.async_mark_available(entity_id)

    def is_unavailable(self, entity_id: str) -> bool:
        """Return true if an entity is currently unavailable."""
        return _is_unavailable_state(self._hass.states.get(entity_id))

    @callback
    def async_fire_monitor_event(self, event: NotificationEvent) -> None:
        """Publish an Object Monitor event on the Home Assistant event bus."""
        self._hass.bus.async_fire(EVENT_OBJECT_MONITOR, event.as_event_data())

    @callback
    def _handle_state_changed_event(self, event: Event) -> None:
        """Handle a Home Assistant state_changed event."""
        entity_id = event.data.get(HA_ATTR_ENTITY_ID)
        if not isinstance(entity_id, str):
            return

        self._hass.async_create_task(self._async_process_state_change(event))

    async def _async_process_state_change(self, event: Event) -> None:
        """Process a state_changed event asynchronously."""
        entity_id = event.data.get(HA_ATTR_ENTITY_ID)
        if not isinstance(entity_id, str):
            return

        labels = self._label_resolver.resolve_entity(entity_id)
        if not labels.is_monitored:
            await self._tracker.async_remove_entity(entity_id)
            self._log_label_skip(labels)
            return

        new_state = event.data.get("new_state")
        if _is_unavailable_state(new_state):
            await self._tracker.async_mark_unavailable(
                labels,
                _friendly_name(entity_id, new_state),
            )
            return

        await self._tracker.async_mark_available(entity_id)

    @callback
    def _handle_entity_registry_updated_event(self, event: Event) -> None:
        """Handle entity registry updates that may change monitoring labels."""
        entity_id = event.data.get(HA_ATTR_ENTITY_ID)

        if isinstance(entity_id, str):
            self._hass.async_create_task(self._async_reconcile_entity(entity_id))
            return

        self._hass.async_create_task(self.async_reconcile())

    async def _async_reconcile_entity(self, entity_id: str) -> None:
        """Reconcile one entity after registry metadata changes."""
        labels = self._label_resolver.resolve_entity(entity_id)
        if not labels.is_monitored:
            await self._tracker.async_remove_entity(entity_id)
            self._log_label_skip(labels)
            return

        state = self._hass.states.get(entity_id)
        if _is_unavailable_state(state):
            await self._tracker.async_mark_unavailable(
                labels,
                _friendly_name(entity_id, state),
            )
        else:
            await self._tracker.async_mark_available(entity_id)

    def _log_label_skip(self, labels: EntityLabels) -> None:
        """Log useful warnings for entities that look misconfigured."""
        if labels.status is LabelResolutionStatus.NOT_MONITORED:
            return

        _LOGGER.warning(
            "Skipping Object Monitor entity %s: %s",
            labels.entity_id,
            labels.reason or labels.status.value,
        )


def _is_unavailable_state(state: Any) -> bool:
    """Return true when a state object represents an unavailable entity."""
    return isinstance(state, State) and state.state == STATE_UNAVAILABLE


def _friendly_name(entity_id: str, state: Any) -> str:
    """Return a user-facing entity name."""
    if not isinstance(state, State):
        return entity_id

    return str(state.attributes.get("friendly_name") or entity_id)
