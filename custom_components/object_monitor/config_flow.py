"""Config flow for the Object Monitor integration."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_DEBUG_LOGGING,
    CONF_HEARTBEAT_INTERVAL,
    CONF_MONITORING_TIMEOUT,
    CONF_NOTIFICATION_MODE,
    CONF_NOTIFICATION_PROVIDER,
    CONF_OBJECT_LABELS,
    DEFAULT_DEBUG_LOGGING,
    DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
    DEFAULT_NAME,
    DEFAULT_NOTIFICATION_MODE,
    DEFAULT_NOTIFICATION_PROVIDER,
    DEFAULT_TIMEOUT_SECONDS,
    DOMAIN,
    LABEL_DEVICE_MONITORING,
    NOTIFICATION_MODE_CATEGORY_ROUTING,
    NOTIFICATION_MODE_SINGLE_ROUTING,
    PROVIDER_TELEGRAM,
    SUPPORTED_CATEGORIES,
)

MIN_TIMEOUT_SECONDS = 1
MAX_TIMEOUT_SECONDS = 86_400
MIN_TIMEOUT_MINUTES = 1
MAX_TIMEOUT_MINUTES = 1_440
LABEL_PATTERN = re.compile(r"^[a-z0-9_]+$")
RESERVED_LABELS = frozenset({LABEL_DEVICE_MONITORING, *SUPPORTED_CATEGORIES})


class ObjectMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Object Monitor."""

    VERSION = 1
    MINOR_VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ObjectMonitorOptionsFlow:
        """Create the options flow."""
        return ObjectMonitorOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the initial user step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}

        if user_input is not None:
            options, errors = _validate_user_input(user_input)
            if not errors:
                return self.async_create_entry(
                    title=DEFAULT_NAME,
                    data={},
                    options=options,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_options_schema(user_input),
            errors=errors,
        )


class ObjectMonitorOptionsFlow(config_entries.OptionsFlow):
    """Handle Object Monitor options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage Object Monitor options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            options, errors = _validate_user_input(user_input)
            if not errors:
                return self.async_create_entry(title="", data=options)

        current_options = _options_for_form(self._config_entry.options)

        return self.async_show_form(
            step_id="init",
            data_schema=_build_options_schema(user_input or current_options),
            errors=errors,
        )


def _build_options_schema(defaults: dict[str, Any] | None) -> vol.Schema:
    """Build the shared config/options form schema."""
    defaults = defaults or {}

    return vol.Schema(
        {
            vol.Required(
                CONF_MONITORING_TIMEOUT,
                default=defaults.get(
                    CONF_MONITORING_TIMEOUT,
                    _seconds_to_minutes(DEFAULT_TIMEOUT_SECONDS),
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_TIMEOUT_MINUTES,
                    max=MAX_TIMEOUT_MINUTES,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_NOTIFICATION_MODE,
                default=defaults.get(
                    CONF_NOTIFICATION_MODE,
                    DEFAULT_NOTIFICATION_MODE,
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        NOTIFICATION_MODE_SINGLE_ROUTING,
                        NOTIFICATION_MODE_CATEGORY_ROUTING,
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_OBJECT_LABELS,
                default=defaults.get(CONF_OBJECT_LABELS, ""),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    multiline=True,
                )
            ),
            vol.Required(
                CONF_NOTIFICATION_PROVIDER,
                default=defaults.get(
                    CONF_NOTIFICATION_PROVIDER,
                    DEFAULT_NOTIFICATION_PROVIDER,
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[PROVIDER_TELEGRAM],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_HEARTBEAT_INTERVAL,
                default=defaults.get(
                    CONF_HEARTBEAT_INTERVAL,
                    DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=86_400,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_DEBUG_LOGGING,
                default=defaults.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING),
            ): selector.BooleanSelector(),
        }
    )


def _validate_user_input(
    user_input: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Validate and normalize config/options flow input."""
    errors: dict[str, str] = {}

    timeout_minutes = _coerce_int(user_input.get(CONF_MONITORING_TIMEOUT))
    if timeout_minutes is None or timeout_minutes < MIN_TIMEOUT_MINUTES:
        errors[CONF_MONITORING_TIMEOUT] = "invalid_timeout"
    elif timeout_minutes > MAX_TIMEOUT_MINUTES:
        errors[CONF_MONITORING_TIMEOUT] = "timeout_too_large"

    timeout_seconds = (
        timeout_minutes * 60
        if timeout_minutes is not None
        else DEFAULT_TIMEOUT_SECONDS
    )

    heartbeat_interval = _coerce_int(user_input.get(CONF_HEARTBEAT_INTERVAL, 0))
    if heartbeat_interval is None or heartbeat_interval < 0:
        errors[CONF_HEARTBEAT_INTERVAL] = "invalid_heartbeat_interval"

    notification_mode = user_input.get(
        CONF_NOTIFICATION_MODE,
        DEFAULT_NOTIFICATION_MODE,
    )
    if notification_mode not in {
        NOTIFICATION_MODE_CATEGORY_ROUTING,
        NOTIFICATION_MODE_SINGLE_ROUTING,
    }:
        errors[CONF_NOTIFICATION_MODE] = "invalid_notification_mode"

    notification_provider = user_input.get(
        CONF_NOTIFICATION_PROVIDER,
        DEFAULT_NOTIFICATION_PROVIDER,
    )
    if notification_provider != PROVIDER_TELEGRAM:
        errors[CONF_NOTIFICATION_PROVIDER] = "invalid_notification_provider"

    object_labels = _normalize_object_labels(user_input.get(CONF_OBJECT_LABELS))
    if not object_labels:
        errors[CONF_OBJECT_LABELS] = "object_labels_required"
    elif any(not LABEL_PATTERN.fullmatch(label) for label in object_labels):
        errors[CONF_OBJECT_LABELS] = "invalid_object_label"
    elif any(label in RESERVED_LABELS for label in object_labels):
        errors[CONF_OBJECT_LABELS] = "reserved_object_label"

    options = {
        CONF_MONITORING_TIMEOUT: timeout_seconds,
        CONF_NOTIFICATION_MODE: notification_mode,
        CONF_OBJECT_LABELS: list(object_labels),
        CONF_NOTIFICATION_PROVIDER: notification_provider,
        CONF_HEARTBEAT_INTERVAL: heartbeat_interval
        if heartbeat_interval is not None
        else DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
        CONF_DEBUG_LOGGING: bool(
            user_input.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING)
        ),
    }

    return options, errors


def _options_for_form(options: Mapping[str, Any]) -> dict[str, Any]:
    """Convert stored options to form defaults."""
    return {
        CONF_MONITORING_TIMEOUT: _seconds_to_minutes(
            options.get(
                CONF_MONITORING_TIMEOUT,
                DEFAULT_TIMEOUT_SECONDS,
            )
        ),
        CONF_NOTIFICATION_MODE: options.get(
            CONF_NOTIFICATION_MODE,
            DEFAULT_NOTIFICATION_MODE,
        ),
        CONF_OBJECT_LABELS: "\n".join(options.get(CONF_OBJECT_LABELS, [])),
        CONF_NOTIFICATION_PROVIDER: options.get(
            CONF_NOTIFICATION_PROVIDER,
            DEFAULT_NOTIFICATION_PROVIDER,
        ),
        CONF_HEARTBEAT_INTERVAL: options.get(
            CONF_HEARTBEAT_INTERVAL,
            DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
        ),
        CONF_DEBUG_LOGGING: options.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING),
    }


def _normalize_object_labels(value: Any) -> tuple[str, ...]:
    """Normalize object label input while preserving user order."""
    if value is None:
        return ()

    if isinstance(value, str):
        raw_labels = re.split(r"[\s,;]+", value)
    elif isinstance(value, list | tuple | set):
        raw_labels = [str(item) for item in value]
    else:
        raw_labels = [str(value)]

    labels: list[str] = []
    seen: set[str] = set()

    for raw_label in raw_labels:
        label = raw_label.strip().lower()
        if not label or label in seen:
            continue
        labels.append(label)
        seen.add(label)

    return tuple(labels)


def _coerce_int(value: Any) -> int | None:
    """Coerce selector input to an integer."""
    if isinstance(value, bool):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _seconds_to_minutes(value: int) -> int:
    """Convert seconds to rounded-up minutes for form defaults."""
    return max(MIN_TIMEOUT_MINUTES, (value + 59) // 60)
