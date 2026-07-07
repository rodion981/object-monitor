"""Runtime composition for the Object Monitor integration."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import logging
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CATEGORY_LABELS,
    CONF_CATEGORY_NAMES,
    CONF_DEBUG_LOGGING,
    CONF_HEARTBEAT_INTERVAL,
    CONF_MONITORING_LABEL,
    CONF_MONITORING_TIMEOUT,
    CONF_OFF_STATE_VALUES,
    CONF_ON_STATE_VALUES,
    CONF_OBJECT_LABELS,
    CONF_OBJECT_NAMES,
    DEFAULT_CATEGORY_LABELS,
    DEFAULT_DEBUG_LOGGING,
    DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
    DEFAULT_MONITORING_LABEL,
    DEFAULT_OFF_STATE_VALUES,
    DEFAULT_ON_STATE_VALUES,
    DEFAULT_TIMEOUT_SECONDS,
)
from .entity_tracker import EntityTracker
from .label_resolver import LabelResolver
from .models import (
    MonitorConfig,
    NotificationEvent,
    NotificationEventType,
    NotificationResult,
)
from .monitor import ObjectMonitor
from .notification_manager import NotificationManager
from .on_off_monitor import OnOffMonitor
from .security_monitor import SecurityMonitor
from .storage import ObjectMonitorStore

_LOGGER = logging.getLogger(__name__)


class ObjectMonitorRuntime:
    """Runtime container for one Object Monitor config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the runtime container."""
        self.hass = hass
        self.entry = entry
        self.config = build_monitor_config(entry.options)
        self.store = ObjectMonitorStore(hass, entry.entry_id)
        self.label_resolver = LabelResolver(hass, self.config)
        self.notification_manager = NotificationManager(hass, self.config)
        self.tracker: EntityTracker | None = None
        self.monitor: ObjectMonitor | None = None
        self.security_monitor: SecurityMonitor | None = None
        self.on_off_monitor: OnOffMonitor | None = None
        self._object_status_listeners: list[Callable[[], None]] = []

    async def async_start(self) -> None:
        """Start all Object Monitor runtime components."""
        stored_state = await self.store.async_load()

        monitor_ref: ObjectMonitor | None = None

        def _is_unavailable(entity_id: str) -> bool:
            if monitor_ref is None:
                return False
            return monitor_ref.is_unavailable(entity_id)

        self.tracker = EntityTracker(
            self.hass,
            self.config,
            self.store,
            self.notification_manager,
            _is_unavailable,
        )
        await self.tracker.async_restore(stored_state)

        self.monitor = ObjectMonitor(
            self.hass,
            self.label_resolver,
            self.tracker,
        )
        monitor_ref = self.monitor
        self.tracker.set_event_callback(self._async_fire_availability_event)
        self.tracker.set_status_callback(self.async_notify_object_status_updated)

        await self.monitor.async_start()
        self.security_monitor = SecurityMonitor(
            self.hass,
            self.config,
            self.notification_manager,
        )
        await self.security_monitor.async_start()
        self.on_off_monitor = OnOffMonitor(
            self.hass,
            self.config,
            self.notification_manager,
        )
        await self.on_off_monitor.async_start()
        self.async_notify_object_status_updated()
        _LOGGER.debug("Object Monitor runtime started")

    async def async_stop(self) -> None:
        """Stop all Object Monitor runtime components."""
        if self.monitor is not None:
            await self.monitor.async_stop()
            self.monitor = None

        if self.security_monitor is not None:
            await self.security_monitor.async_stop()
            self.security_monitor = None

        if self.on_off_monitor is not None:
            await self.on_off_monitor.async_stop()
            self.on_off_monitor = None

        if self.tracker is not None:
            await self.tracker.async_shutdown()
            self.tracker = None

        self._object_status_listeners.clear()

        _LOGGER.debug("Object Monitor runtime stopped")

    def async_add_object_status_listener(
        self,
        update_callback: Callable[[], None],
    ) -> Callable[[], None]:
        """Register a callback for object availability aggregate updates."""
        self._object_status_listeners.append(update_callback)

        def _unsubscribe() -> None:
            if update_callback in self._object_status_listeners:
                self._object_status_listeners.remove(update_callback)

        return _unsubscribe

    def async_notify_object_status_updated(self) -> None:
        """Notify object status entities that availability aggregates changed."""
        for update_callback in tuple(self._object_status_listeners):
            update_callback()

    def _async_fire_availability_event(self, event: NotificationEvent) -> None:
        """Publish an availability event."""
        if self.monitor is not None:
            self.monitor.async_fire_monitor_event(event)

    async def async_reload_monitored_entities(self) -> None:
        """Reconcile monitored entities from current registry and state."""
        if self.monitor is not None:
            await self.monitor.async_reconcile()
        if self.security_monitor is not None:
            await self.security_monitor.async_reconcile()
        if self.on_off_monitor is not None:
            await self.on_off_monitor.async_reconcile()
        self.async_notify_object_status_updated()

    async def async_clear_entity_state(self, entity_id: str) -> None:
        """Clear stored and in-memory monitor state for one entity."""
        if self.tracker is not None:
            await self.tracker.async_remove_entity(entity_id)
            self.async_notify_object_status_updated()
            return

        await self.store.async_remove_entity(entity_id)
        self.async_notify_object_status_updated()

    async def async_send_test_notification(
        self,
        object_label: str,
        category: str | None,
        event_type: NotificationEventType,
        entity_id: str,
        friendly_name: str,
    ) -> NotificationResult:
        """Emit a test availability event."""
        event = NotificationEvent(
            event_type=event_type,
            entity_id=entity_id,
            friendly_name=friendly_name,
            object_label=object_label,
            category=category,
            notified_at=datetime.now(timezone.utc),
            timeout_seconds=self.config.monitoring_timeout,
        )
        self.hass.bus.async_fire(event.ha_event_type, event.as_event_data())
        return await self.notification_manager.async_notify(event)

    def diagnostics(self) -> dict[str, Any]:
        """Return non-sensitive runtime diagnostics."""
        entities = self.tracker.entities if self.tracker is not None else {}

        return {
            "monitoring_label": self.config.monitoring_label,
            "category_labels": list(self.config.category_labels),
            "monitoring_timeout": self.config.monitoring_timeout,
            "object_labels": list(self.config.object_labels),
            "object_names": dict(self.config.object_names),
            "debug_logging": self.config.debug_logging,
            "category_names": dict(self.config.category_names),
            "on_state_values": list(self.config.on_state_values),
            "off_state_values": list(self.config.off_state_values),
            "heartbeat_interval": self.config.heartbeat_interval,
            "tracked_entities": len(entities),
            "pending_entities": self.tracker.pending_count
            if self.tracker is not None
            else 0,
            "offline_entities": self.tracker.offline_count
            if self.tracker is not None
            else 0,
            "security_tracked_entities": self.security_monitor.tracked_count
            if self.security_monitor is not None
            else 0,
            "on_off_tracked_entities": self.on_off_monitor.tracked_count
            if self.on_off_monitor is not None
            else 0,
        }


def build_monitor_config(options: Mapping[str, Any]) -> MonitorConfig:
    """Build a typed monitor config from config entry options."""
    return MonitorConfig(
        monitoring_label=str(
            options.get(CONF_MONITORING_LABEL, DEFAULT_MONITORING_LABEL)
        ),
        category_labels=tuple(
            options.get(CONF_CATEGORY_LABELS, DEFAULT_CATEGORY_LABELS)
        ),
        monitoring_timeout=int(
            options.get(CONF_MONITORING_TIMEOUT, DEFAULT_TIMEOUT_SECONDS)
        ),
        object_labels=tuple(options.get(CONF_OBJECT_LABELS, ())),
        object_names=dict(options.get(CONF_OBJECT_NAMES, {})),
        category_names=dict(options.get(CONF_CATEGORY_NAMES, {})),
        on_state_values=tuple(
            options.get(CONF_ON_STATE_VALUES, DEFAULT_ON_STATE_VALUES)
        ),
        off_state_values=tuple(
            options.get(CONF_OFF_STATE_VALUES, DEFAULT_OFF_STATE_VALUES)
        ),
        debug_logging=bool(options.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING)),
        heartbeat_interval=int(
            options.get(CONF_HEARTBEAT_INTERVAL, DEFAULT_HEARTBEAT_INTERVAL_SECONDS)
        ),
    )
