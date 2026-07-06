"""Entity state tracking for the Object Monitor integration."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime, timezone
import logging

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later

from .models import (
    EntityLabels,
    MonitoredEntity,
    MonitorConfig,
    NotificationEvent,
    NotificationEventType,
    StoredEntityState,
    StoredMonitorState,
)
from .notification_manager import NotificationManager
from .storage import ObjectMonitorStore

_LOGGER = logging.getLogger(__name__)

IsUnavailableCallback = Callable[[str], bool]
EventCallback = Callable[[NotificationEvent], None]


class EntityTracker:
    """Track unavailable state, timers, and notifications for entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: MonitorConfig,
        store: ObjectMonitorStore,
        notification_manager: NotificationManager,
        is_unavailable: IsUnavailableCallback,
        event_callback: EventCallback | None = None,
    ) -> None:
        """Initialize the entity tracker."""
        self._hass = hass
        self._config = config
        self._store = store
        self._notification_manager = notification_manager
        self._is_unavailable = is_unavailable
        self._event_callback = event_callback
        self._entities: dict[str, MonitoredEntity] = {}
        self._timers: dict[str, CALLBACK_TYPE] = {}

    @property
    def entities(self) -> dict[str, MonitoredEntity]:
        """Return currently tracked entities."""
        return dict(self._entities)

    @property
    def pending_count(self) -> int:
        """Return the number of entities waiting for timeout expiration."""
        return sum(1 for entity in self._entities.values() if entity.is_pending)

    @property
    def offline_count(self) -> int:
        """Return the number of entities confirmed offline."""
        return sum(1 for entity in self._entities.values() if entity.is_offline)

    def set_event_callback(self, event_callback: EventCallback | None) -> None:
        """Set the callback used to publish monitor events."""
        self._event_callback = event_callback

    async def async_restore(self, state: StoredMonitorState) -> None:
        """Restore tracker state after Home Assistant restart."""
        for stored_entity in state.entities.values():
            entity = _stored_to_monitored_entity(stored_entity)
            self._entities[entity.entity_id] = entity

            if entity.is_pending:
                self._schedule_timer(
                    entity.entity_id,
                    self._remaining_timeout(entity),
                )

    async def async_mark_unavailable(
        self,
        labels: EntityLabels,
        friendly_name: str,
    ) -> None:
        """Mark an entity as unavailable and start a timeout if needed."""
        if not labels.object_label:
            _LOGGER.debug(
                "Ignoring unavailable entity %s without object label",
                labels.entity_id,
            )
            return

        entity = self._entities.get(labels.entity_id)
        old_timeout_seconds = entity.timeout_seconds if entity is not None else None
        if entity is None:
            timeout_seconds = labels.timeout_seconds or self._config.monitoring_timeout
            entity = MonitoredEntity(
                entity_id=labels.entity_id,
                object_label=labels.object_label,
                category=labels.category,
                friendly_name=friendly_name,
                timeout_seconds=timeout_seconds,
                unavailable_since=_utcnow(),
            )
            self._entities[labels.entity_id] = entity
        else:
            entity.object_label = labels.object_label
            entity.category = labels.category
            entity.friendly_name = friendly_name
            entity.timeout_seconds = (
                labels.timeout_seconds or self._config.monitoring_timeout
            )
            if entity.unavailable_since is None:
                entity.unavailable_since = _utcnow()

        if entity.is_offline:
            await self._store.async_save_entity(entity)
            return

        timeout_changed = (
            old_timeout_seconds is not None
            and old_timeout_seconds != entity.timeout_seconds
        )
        if labels.entity_id not in self._timers or timeout_changed:
            self._schedule_timer(labels.entity_id, self._remaining_timeout(entity))

        await self._store.async_save_entity(entity)

    async def async_mark_available(self, entity_id: str) -> None:
        """Mark an entity as available and send recovery if needed."""
        self._cancel_timer(entity_id)
        entity = self._entities.pop(entity_id, None)

        if entity is None:
            await self._store.async_remove_entity(entity_id)
            return

        if entity.notified_offline:
            event = NotificationEvent(
                event_type=NotificationEventType.RECOVERY,
                entity_id=entity.entity_id,
                friendly_name=entity.friendly_name,
                object_label=entity.object_label,
                category=entity.category,
                unavailable_since=entity.unavailable_since,
                notified_at=_utcnow(),
                timeout_seconds=entity.timeout_seconds,
            )
            self._emit_event(event)
            await self._notification_manager.async_notify(event)

        await self._store.async_remove_entity(entity_id)

    async def async_remove_entity(self, entity_id: str) -> None:
        """Stop tracking one entity and remove its persisted state."""
        self._cancel_timer(entity_id)
        self._entities.pop(entity_id, None)
        await self._store.async_remove_entity(entity_id)

    async def async_prune_except(self, active_entity_ids: Iterable[str]) -> None:
        """Remove tracked entities that are no longer monitor candidates."""
        active = set(active_entity_ids)
        stale_entity_ids = [
            entity_id for entity_id in self._entities if entity_id not in active
        ]

        for entity_id in stale_entity_ids:
            self._cancel_timer(entity_id)
            self._entities.pop(entity_id, None)

        await self._store.async_prune_except(active)

    async def async_shutdown(self) -> None:
        """Cancel all pending timers."""
        for entity_id in list(self._timers):
            self._cancel_timer(entity_id)

    def _schedule_timer(self, entity_id: str, delay: float) -> None:
        """Schedule a timeout callback for an entity."""
        self._cancel_timer(entity_id)

        @callback
        def _handle_timeout(now: datetime) -> None:
            self._timers.pop(entity_id, None)
            self._hass.add_job(self._async_timeout_expired, entity_id)

        self._timers[entity_id] = async_call_later(
            self._hass,
            max(0, delay),
            _handle_timeout,
        )

    def _cancel_timer(self, entity_id: str) -> None:
        """Cancel a pending timeout callback."""
        if cancel := self._timers.pop(entity_id, None):
            cancel()

    async def _async_timeout_expired(self, entity_id: str) -> None:
        """Handle an entity timeout expiration."""
        entity = self._entities.get(entity_id)
        if entity is None or not entity.is_pending:
            return

        if not self._is_unavailable(entity_id):
            self._entities.pop(entity_id, None)
            await self._store.async_remove_entity(entity_id)
            return

        entity.offline_confirmed = True

        event = NotificationEvent(
            event_type=NotificationEventType.OFFLINE,
            entity_id=entity.entity_id,
            friendly_name=entity.friendly_name,
            object_label=entity.object_label,
            category=entity.category,
            unavailable_since=entity.unavailable_since,
            notified_at=_utcnow(),
            timeout_seconds=entity.timeout_seconds,
        )
        self._emit_event(event)

        result = await self._notification_manager.async_notify(event)
        if result.success:
            entity.notified_offline = True
            entity.last_notification_type = NotificationEventType.OFFLINE
            entity.last_notified_at = event.notified_at

        await self._store.async_save_entity(entity)

    def _remaining_timeout(self, entity: MonitoredEntity) -> float:
        """Calculate remaining timeout seconds for restored pending state."""
        if entity.unavailable_since is None:
            return float(entity.timeout_seconds)

        elapsed = (_utcnow() - entity.unavailable_since).total_seconds()
        return max(0, entity.timeout_seconds - elapsed)

    def _emit_event(self, event: NotificationEvent) -> None:
        """Emit an optional callback event to the monitor/runtime layer."""
        if self._event_callback is not None:
            self._event_callback(event)


def _stored_to_monitored_entity(stored: StoredEntityState) -> MonitoredEntity:
    """Convert persisted entity state to in-memory tracker state."""
    return MonitoredEntity(
        entity_id=stored.entity_id,
        object_label=stored.object_label,
        category=stored.category,
        friendly_name=stored.friendly_name,
        timeout_seconds=stored.timeout_seconds,
        unavailable_since=stored.unavailable_since,
        offline_confirmed=stored.offline_confirmed,
        notified_offline=stored.notified_offline,
        last_notification_type=stored.last_notification_type,
        last_notified_at=stored.last_notified_at,
    )


def _utcnow() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)
