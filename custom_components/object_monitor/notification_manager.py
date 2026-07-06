"""Event delivery acknowledgement for the Object Monitor integration."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .models import (
    MonitorNotificationEvent,
    MonitorConfig,
    NotificationResult,
)

_LOGGER = logging.getLogger(__name__)


class NotificationManager:
    """Acknowledge monitor events after they are emitted to Home Assistant."""

    def __init__(self, hass: HomeAssistant, config: MonitorConfig) -> None:
        """Initialize the notification manager."""
        self._hass = hass
        self._config = config

    async def async_notify(
        self,
        event: MonitorNotificationEvent,
    ) -> NotificationResult:
        """Acknowledge that the monitor event was emitted to Home Assistant."""
        _LOGGER.debug("Object Monitor event emitted for %s", event.entity_id)
        return NotificationResult(success=True, target="event_bus")
