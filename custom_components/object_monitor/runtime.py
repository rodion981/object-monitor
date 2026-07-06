"""Runtime composition for the Object Monitor integration."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_DEBUG_LOGGING,
    CONF_HEARTBEAT_INTERVAL,
    CONF_MONITORING_TIMEOUT,
    CONF_NOTIFICATION_MODE,
    CONF_NOTIFICATION_PROVIDER,
    CONF_OBJECT_LABELS,
    DEFAULT_DEBUG_LOGGING,
    DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
    DEFAULT_NOTIFICATION_MODE,
    DEFAULT_NOTIFICATION_PROVIDER,
    DEFAULT_TIMEOUT_SECONDS,
)
from .entity_tracker import EntityTracker
from .label_resolver import LabelResolver
from .models import (
    MonitorConfig,
    NotificationEvent,
    NotificationEventType,
    NotificationMode,
    NotificationResult,
    ProviderType,
)
from .monitor import ObjectMonitor
from .notification_manager import NotificationManager
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
        self.tracker.set_event_callback(self.monitor.async_fire_monitor_event)

        await self.monitor.async_start()
        _LOGGER.debug("Object Monitor runtime started")

    async def async_stop(self) -> None:
        """Stop all Object Monitor runtime components."""
        if self.monitor is not None:
            await self.monitor.async_stop()
            self.monitor = None

        if self.tracker is not None:
            await self.tracker.async_shutdown()
            self.tracker = None

        _LOGGER.debug("Object Monitor runtime stopped")

    async def async_reload_monitored_entities(self) -> None:
        """Reconcile monitored entities from current registry and state."""
        if self.monitor is not None:
            await self.monitor.async_reconcile()

    async def async_clear_entity_state(self, entity_id: str) -> None:
        """Clear stored and in-memory monitor state for one entity."""
        if self.tracker is not None:
            await self.tracker.async_remove_entity(entity_id)
            return

        await self.store.async_remove_entity(entity_id)

    async def async_send_test_notification(
        self,
        object_label: str,
        category: str | None,
        event_type: NotificationEventType,
        entity_id: str,
        friendly_name: str,
    ) -> NotificationResult:
        """Send a test notification through the configured provider."""
        event = NotificationEvent(
            event_type=event_type,
            entity_id=entity_id,
            friendly_name=friendly_name,
            object_label=object_label,
            category=category,
            notified_at=datetime.now(timezone.utc),
            timeout_seconds=self.config.monitoring_timeout,
        )
        return await self.notification_manager.async_notify(event)

    def diagnostics(self) -> dict[str, Any]:
        """Return non-sensitive runtime diagnostics."""
        entities = self.tracker.entities if self.tracker is not None else {}

        return {
            "monitoring_timeout": self.config.monitoring_timeout,
            "notification_mode": self.config.notification_mode.value,
            "notification_provider": self.config.notification_provider.value,
            "object_labels": list(self.config.object_labels),
            "debug_logging": self.config.debug_logging,
            "heartbeat_interval": self.config.heartbeat_interval,
            "tracked_entities": len(entities),
            "pending_entities": self.tracker.pending_count
            if self.tracker is not None
            else 0,
            "offline_entities": self.tracker.offline_count
            if self.tracker is not None
            else 0,
        }


def build_monitor_config(options: Mapping[str, Any]) -> MonitorConfig:
    """Build a typed monitor config from config entry options."""
    return MonitorConfig(
        monitoring_timeout=int(
            options.get(CONF_MONITORING_TIMEOUT, DEFAULT_TIMEOUT_SECONDS)
        ),
        notification_mode=NotificationMode(
            options.get(CONF_NOTIFICATION_MODE, DEFAULT_NOTIFICATION_MODE)
        ),
        object_labels=tuple(options.get(CONF_OBJECT_LABELS, ())),
        debug_logging=bool(options.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING)),
        notification_provider=ProviderType(
            options.get(CONF_NOTIFICATION_PROVIDER, DEFAULT_NOTIFICATION_PROVIDER)
        ),
        heartbeat_interval=int(
            options.get(CONF_HEARTBEAT_INTERVAL, DEFAULT_HEARTBEAT_INTERVAL_SECONDS)
        ),
    )
