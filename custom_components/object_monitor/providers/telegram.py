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
    MonitorNotificationEvent,
    MonitorConfig,
    NotificationEvent,
    NotificationEventType,
    NotificationMode,
    NotificationResult,
    SecurityStateEvent,
    SecuritySystemState,
)
from .base import NotificationProvider

_LOGGER = logging.getLogger(__name__)


class TelegramProvider(NotificationProvider):
    """Send Object Monitor notifications through Telegram scripts."""

    def __init__(self, hass: HomeAssistant, config: MonitorConfig) -> None:
        """Initialize the Telegram provider."""
        self._hass = hass
        self._config = config

    async def async_send(self, event: MonitorNotificationEvent) -> NotificationResult:
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
                {"message": _format_message(event, self._config)},
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


def _format_message(
    event: MonitorNotificationEvent,
    config: MonitorConfig,
) -> str:
    """Format an Object Monitor event as a Telegram message."""
    if isinstance(event, SecurityStateEvent):
        return _format_security_message(event, config)

    return _format_availability_message(event, config)


def _format_availability_message(
    event: NotificationEvent,
    config: MonitorConfig,
) -> str:
    """Format an availability event as a Telegram message."""
    object_name = config.object_display_name(event.object_label)
    category = (
        config.category_display_name(event.category)
        if event.category
        else "не вказано"
    )

    if event.event_type is NotificationEventType.OFFLINE:
        return (
            f"\U0001f534 {event.friendly_name} недоступний\n\n"
            f"Об'єкт: {object_name}\n"
            f"Категорія: {category}\n"
            f"Сутність: {event.entity_id}"
        )

    return (
        f"\U0001f7e2 {event.friendly_name} відновлено\n\n"
        f"Об'єкт: {object_name}\n"
        f"Категорія: {category}\n"
        f"Сутність: {event.entity_id}"
    )


def _format_security_message(
    event: SecurityStateEvent,
    config: MonitorConfig,
) -> str:
    """Format a security system state event as a Telegram message."""
    object_name = config.object_display_name(event.object_label)
    details = _security_state_details(event.state)
    title = details["title"]
    if (
        event.previous_state is SecuritySystemState.UNAVAILABLE
        and event.state is not SecuritySystemState.UNAVAILABLE
    ):
        title = "\U0001f7e2 Зв'язок із системою охорони відновлено"

    lines = [
        title,
        "",
        f"Об'єкт: {object_name}",
        "",
    ]

    if details["mode"]:
        lines.extend(["Режим:", details["mode"], ""])

    lines.extend(
        [
            "Стан:",
            details["state"],
            "",
            "Сутність:",
            event.entity_id,
        ]
    )

    if event.notified_at is not None:
        lines.extend(["", "Час:", event.notified_at.astimezone().strftime("%H:%M")])

    if details["priority"]:
        lines.extend(["", details["priority"]])

    return "\n".join(lines)


def _security_state_details(state: SecuritySystemState) -> dict[str, str]:
    """Return user-facing message parts for a security system state."""
    return {
        SecuritySystemState.DISARMED: {
            "title": "\U0001f513 Систему охорони знято",
            "mode": "",
            "state": "Знято з охорони",
            "priority": "",
        },
        SecuritySystemState.ARMED_HOME: {
            "title": "\U0001f3e0 Увімкнено режим вдома",
            "mode": "Вдома",
            "state": "Під охороною",
            "priority": "",
        },
        SecuritySystemState.ARMED_AWAY: {
            "title": "\U0001f6e1 Систему охорони увімкнено",
            "mode": "Немає вдома",
            "state": "Під охороною",
            "priority": "",
        },
        SecuritySystemState.ARMED_NIGHT: {
            "title": "\U0001f319 Увімкнено нічний режим",
            "mode": "Ніч",
            "state": "Під охороною",
            "priority": "",
        },
        SecuritySystemState.ARMED_VACATION: {
            "title": "\U0001f6e1 Увімкнено режим відпустки",
            "mode": "Відпустка",
            "state": "Під охороною",
            "priority": "",
        },
        SecuritySystemState.ARMING: {
            "title": "\u23f3 Система охорони вмикається",
            "mode": "",
            "state": "Вмикається",
            "priority": "",
        },
        SecuritySystemState.PENDING: {
            "title": "\u26a0 Почалась затримка входу/виходу",
            "mode": "",
            "state": "Затримка",
            "priority": "",
        },
        SecuritySystemState.TRIGGERED: {
            "title": "\U0001f6a8 ТРИВОГА ОХОРОНИ",
            "mode": "",
            "state": "Тривога",
            "priority": "Високий пріоритет.",
        },
        SecuritySystemState.UNKNOWN: {
            "title": "\u26a0 Стан системи охорони невідомий",
            "mode": "",
            "state": "Невідомо",
            "priority": "",
        },
        SecuritySystemState.UNAVAILABLE: {
            "title": "\U0001f534 Система охорони недоступна",
            "mode": "",
            "state": "Недоступна",
            "priority": "",
        },
    }[state]
