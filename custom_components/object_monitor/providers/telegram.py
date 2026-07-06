"""Telegram notification provider using Home Assistant scripts."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from ..const import (
    SCRIPT_DOMAIN,
    TELEGRAM_SCRIPT_PREFIX,
)
from ..models import (
    MonitorConfig,
    NotificationEvent,
    NotificationEventType,
    NotificationMode,
    NotificationResult,
)
from .base import NotificationProvider

_LOGGER = logging.getLogger(__name__)


class TelegramProvider(NotificationProvider):
    """Send Object Monitor notifications through Telegram scripts."""

    def __init__(self, hass: HomeAssistant, config: MonitorConfig) -> None:
        """Initialize the Telegram provider."""
        self._hass = hass
        self._config = config

    async def async_send(self, event: NotificationEvent) -> NotificationResult:
        """Send a notification through the configured Telegram script route."""
        script_entity_id = self._script_entity_id(event)

        if script_entity_id is None:
            _LOGGER.warning(
                "Skipping notification for %s because category routing requires "
                "a valid category",
                event.entity_id,
            )
            return NotificationResult(
                success=False,
                reason="missing_category",
            )

        if self._hass.states.get(script_entity_id) is None:
            _LOGGER.warning(
                "Telegram notification script %s is missing for %s",
                script_entity_id,
                event.entity_id,
            )
            return NotificationResult(
                success=False,
                target=script_entity_id,
                reason="missing_script",
            )

        try:
            await self._hass.services.async_call(
                SCRIPT_DOMAIN,
                _script_service_name(script_entity_id),
                {"message": _format_message(event)},
                blocking=True,
            )
        except HomeAssistantError as err:
            _LOGGER.warning(
                "Telegram notification script %s failed for %s: %s",
                script_entity_id,
                event.entity_id,
                err,
            )
            return NotificationResult(
                success=False,
                target=script_entity_id,
                reason="script_call_failed",
            )

        return NotificationResult(success=True, target=script_entity_id)

    def _script_entity_id(self, event: NotificationEvent) -> str | None:
        """Build the target script entity ID for a notification event."""
        if self._config.notification_mode is NotificationMode.CATEGORY_ROUTING:
            if not event.category:
                return None
            return (
                f"{SCRIPT_DOMAIN}.{TELEGRAM_SCRIPT_PREFIX}_"
                f"{event.object_label}_{event.category}"
            )

        return f"{SCRIPT_DOMAIN}.{TELEGRAM_SCRIPT_PREFIX}_{event.object_label}"


def _script_service_name(script_entity_id: str) -> str:
    """Return the script service name from a script entity ID."""
    return script_entity_id.split(".", 1)[1]


def _format_message(event: NotificationEvent) -> str:
    """Format an Object Monitor event as a Telegram message."""
    category = event.category or "не вказано"

    if event.event_type is NotificationEventType.OFFLINE:
        return (
            f"\U0001f534 {event.friendly_name}\n\n"
            "Сутність\n"
            f"{event.entity_id}\n\n"
            "Об'єкт\n"
            f"{event.object_label}\n\n"
            "Категорія\n"
            f"{category}\n\n"
            f"Недоступна понад {_format_duration(event.timeout_seconds)}."
        )

    return (
        f"\U0001f7e2 {event.friendly_name}\n\n"
        "Відновлено.\n\n"
        "Сутність\n"
        f"{event.entity_id}\n\n"
        "Об'єкт\n"
        f"{event.object_label}\n\n"
        "Категорія\n"
        f"{category}"
    )


def _format_duration(seconds: int) -> str:
    """Format a duration in Ukrainian."""
    if seconds < 60:
        return f"{seconds} {_plural(seconds, 'секунду', 'секунди', 'секунд')}"

    minutes = round(seconds / 60)
    return f"{minutes} {_plural(minutes, 'хвилину', 'хвилини', 'хвилин')}"


def _plural(value: int, one: str, few: str, many: str) -> str:
    """Return the Ukrainian plural form for a positive integer."""
    last_two = value % 100
    last = value % 10
    if 11 <= last_two <= 14:
        return many
    if last == 1:
        return one
    if 2 <= last <= 4:
        return few
    return many
