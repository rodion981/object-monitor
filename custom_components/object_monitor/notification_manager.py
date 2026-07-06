"""Notification orchestration for the Object Monitor integration."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .models import (
    MonitorConfig,
    NotificationEvent,
    NotificationResult,
    ProviderType,
)
from .providers.base import NotificationProvider
from .providers.telegram import TelegramProvider

_LOGGER = logging.getLogger(__name__)


class NotificationManager:
    """Route monitor events to the configured notification provider."""

    def __init__(self, hass: HomeAssistant, config: MonitorConfig) -> None:
        """Initialize the notification manager."""
        self._hass = hass
        self._config = config
        self._provider = self._build_provider(config.notification_provider)

    async def async_notify(self, event: NotificationEvent) -> NotificationResult:
        """Send a provider-neutral notification event."""
        result = await self._provider.async_send(event)

        if result.success:
            _LOGGER.debug(
                "Notification for %s delivered to %s",
                event.entity_id,
                result.target,
            )
        else:
            _LOGGER.warning(
                "Notification for %s was not delivered: %s",
                event.entity_id,
                result.reason or "unknown_reason",
            )

        return result

    def _build_provider(self, provider_type: ProviderType) -> NotificationProvider:
        """Build the configured notification provider."""
        if provider_type is ProviderType.TELEGRAM:
            return TelegramProvider(self._hass, self._config)

        raise ValueError(f"Unsupported notification provider: {provider_type}")
