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
    DEFAULT_NAME,
    DEFAULT_OFF_STATE_VALUES,
    DEFAULT_ON_STATE_VALUES,
    DEFAULT_TIMEOUT_SECONDS,
    DOMAIN,
)

MIN_TIMEOUT_SECONDS = 1
MAX_TIMEOUT_SECONDS = 86_400
LABEL_PATTERN = re.compile(r"^[a-z0-9_]+$")


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
                CONF_MONITORING_LABEL,
                default=defaults.get(CONF_MONITORING_LABEL, DEFAULT_MONITORING_LABEL),
            ): selector.TextSelector(),
            vol.Required(
                CONF_OBJECT_LABELS,
                default=defaults.get(CONF_OBJECT_LABELS, ""),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    multiline=True,
                )
            ),
            vol.Optional(
                CONF_OBJECT_NAMES,
                default=defaults.get(CONF_OBJECT_NAMES, ""),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    multiline=True,
                )
            ),
            vol.Optional(
                CONF_CATEGORY_LABELS,
                default=defaults.get(
                    CONF_CATEGORY_LABELS,
                    "\n".join(DEFAULT_CATEGORY_LABELS),
                ),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    multiline=True,
                )
            ),
            vol.Optional(
                CONF_CATEGORY_NAMES,
                default=defaults.get(CONF_CATEGORY_NAMES, ""),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    multiline=True,
                )
            ),
            vol.Optional(
                CONF_ON_STATE_VALUES,
                default=defaults.get(
                    CONF_ON_STATE_VALUES,
                    "\n".join(DEFAULT_ON_STATE_VALUES),
                ),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    multiline=True,
                )
            ),
            vol.Optional(
                CONF_OFF_STATE_VALUES,
                default=defaults.get(
                    CONF_OFF_STATE_VALUES,
                    "\n".join(DEFAULT_OFF_STATE_VALUES),
                ),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    multiline=True,
                )
            ),
            vol.Required(
                CONF_MONITORING_TIMEOUT,
                default=defaults.get(
                    CONF_MONITORING_TIMEOUT,
                    _seconds_to_duration(DEFAULT_TIMEOUT_SECONDS),
                ),
            ): selector.DurationSelector(
                selector.DurationSelectorConfig(enable_day=False)
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

    timeout_seconds = _coerce_duration_seconds(
        user_input.get(CONF_MONITORING_TIMEOUT)
    )
    if timeout_seconds is None or timeout_seconds < MIN_TIMEOUT_SECONDS:
        errors[CONF_MONITORING_TIMEOUT] = "invalid_timeout"
    elif timeout_seconds > MAX_TIMEOUT_SECONDS:
        errors[CONF_MONITORING_TIMEOUT] = "timeout_too_large"

    heartbeat_interval = _coerce_int(user_input.get(CONF_HEARTBEAT_INTERVAL, 0))
    if heartbeat_interval is None or heartbeat_interval < 0:
        errors[CONF_HEARTBEAT_INTERVAL] = "invalid_heartbeat_interval"

    monitoring_label = _normalize_single_label(
        user_input.get(CONF_MONITORING_LABEL, DEFAULT_MONITORING_LABEL)
    )
    if not monitoring_label:
        errors[CONF_MONITORING_LABEL] = "monitoring_label_required"
    elif not LABEL_PATTERN.fullmatch(monitoring_label):
        errors[CONF_MONITORING_LABEL] = "invalid_monitoring_label"

    category_labels = _normalize_labels(user_input.get(CONF_CATEGORY_LABELS))
    if any(not LABEL_PATTERN.fullmatch(label) for label in category_labels):
        errors[CONF_CATEGORY_LABELS] = "invalid_category_label"
    elif monitoring_label and monitoring_label in category_labels:
        errors[CONF_CATEGORY_LABELS] = "monitoring_category_overlap"

    object_labels = _normalize_labels(user_input.get(CONF_OBJECT_LABELS))
    if not object_labels:
        errors[CONF_OBJECT_LABELS] = "object_labels_required"
    elif any(not LABEL_PATTERN.fullmatch(label) for label in object_labels):
        errors[CONF_OBJECT_LABELS] = "invalid_object_label"
    elif monitoring_label and monitoring_label in object_labels:
        errors[CONF_OBJECT_LABELS] = "monitoring_object_overlap"
    elif set(object_labels) & set(category_labels):
        errors[CONF_OBJECT_LABELS] = "category_object_overlap"

    object_names, object_name_error = _normalize_label_names(
        user_input.get(CONF_OBJECT_NAMES)
    )
    if object_name_error:
        errors[CONF_OBJECT_NAMES] = object_name_error
    elif set(object_names) - set(object_labels):
        errors[CONF_OBJECT_NAMES] = "unknown_object_name_label"

    category_names, category_name_error = _normalize_label_names(
        user_input.get(CONF_CATEGORY_NAMES)
    )
    if category_name_error:
        errors[CONF_CATEGORY_NAMES] = category_name_error
    elif set(category_names) - set(category_labels):
        errors[CONF_CATEGORY_NAMES] = "unknown_category_name_label"

    on_state_values = _normalize_state_values(
        user_input.get(CONF_ON_STATE_VALUES),
        DEFAULT_ON_STATE_VALUES,
    )
    off_state_values = _normalize_state_values(
        user_input.get(CONF_OFF_STATE_VALUES),
        DEFAULT_OFF_STATE_VALUES,
    )
    if not on_state_values:
        errors[CONF_ON_STATE_VALUES] = "on_state_values_required"
    elif not off_state_values:
        errors[CONF_OFF_STATE_VALUES] = "off_state_values_required"
    elif set(on_state_values) & set(off_state_values):
        errors[CONF_OFF_STATE_VALUES] = "on_off_state_overlap"

    options = {
        CONF_MONITORING_LABEL: monitoring_label or DEFAULT_MONITORING_LABEL,
        CONF_CATEGORY_LABELS: list(category_labels),
        CONF_MONITORING_TIMEOUT: timeout_seconds or DEFAULT_TIMEOUT_SECONDS,
        CONF_OBJECT_LABELS: list(object_labels),
        CONF_OBJECT_NAMES: object_names,
        CONF_CATEGORY_NAMES: category_names,
        CONF_ON_STATE_VALUES: list(on_state_values),
        CONF_OFF_STATE_VALUES: list(off_state_values),
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
        CONF_MONITORING_LABEL: options.get(
            CONF_MONITORING_LABEL,
            DEFAULT_MONITORING_LABEL,
        ),
        CONF_CATEGORY_LABELS: "\n".join(
            options.get(CONF_CATEGORY_LABELS, DEFAULT_CATEGORY_LABELS)
        ),
        CONF_MONITORING_TIMEOUT: _seconds_to_duration(
            options.get(
                CONF_MONITORING_TIMEOUT,
                DEFAULT_TIMEOUT_SECONDS,
            )
        ),
        CONF_OBJECT_LABELS: "\n".join(options.get(CONF_OBJECT_LABELS, [])),
        CONF_OBJECT_NAMES: _label_names_for_form(options.get(CONF_OBJECT_NAMES, {})),
        CONF_CATEGORY_NAMES: _label_names_for_form(
            options.get(CONF_CATEGORY_NAMES, {})
        ),
        CONF_ON_STATE_VALUES: "\n".join(
            options.get(CONF_ON_STATE_VALUES, DEFAULT_ON_STATE_VALUES)
        ),
        CONF_OFF_STATE_VALUES: "\n".join(
            options.get(CONF_OFF_STATE_VALUES, DEFAULT_OFF_STATE_VALUES)
        ),
        CONF_HEARTBEAT_INTERVAL: options.get(
            CONF_HEARTBEAT_INTERVAL,
            DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
        ),
        CONF_DEBUG_LOGGING: options.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING),
    }


def _normalize_single_label(value: Any) -> str:
    """Normalize a single label value."""
    if value is None:
        return ""
    return str(value).strip().lower()


def _normalize_labels(value: Any) -> tuple[str, ...]:
    """Normalize label input while preserving user order."""
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


def _normalize_state_values(
    value: Any,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    """Normalize custom state values while preserving user order."""
    values = _normalize_labels(value)
    return values or default


def _normalize_label_names(value: Any) -> tuple[dict[str, str], str | None]:
    """Normalize label display name input from key=value lines."""
    if value is None:
        return {}, None

    if isinstance(value, Mapping):
        raw_items = value.items()
    else:
        raw_items = []
        for line in str(value).splitlines():
            line = line.strip()
            if not line:
                continue
            separator = "=" if "=" in line else ":" if ":" in line else None
            if separator is None:
                return {}, "invalid_label_name_mapping"
            key, display_name = line.split(separator, 1)
            raw_items.append((key, display_name))

    names: dict[str, str] = {}
    for raw_key, raw_display_name in raw_items:
        key = str(raw_key).strip().lower()
        display_name = str(raw_display_name).strip()
        if not key or not display_name:
            return {}, "invalid_label_name_mapping"
        if not LABEL_PATTERN.fullmatch(key):
            return {}, "invalid_label_name_label"
        names[key] = display_name

    return names, None


def _label_names_for_form(value: Any) -> str:
    """Format stored label display names for multiline form defaults."""
    if not isinstance(value, Mapping):
        return ""
    return "\n".join(f"{key}={name}" for key, name in value.items())


def _coerce_int(value: Any) -> int | None:
    """Coerce selector input to an integer."""
    if isinstance(value, bool):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_duration_seconds(value: Any) -> int | None:
    """Coerce duration selector input to total seconds."""
    if isinstance(value, Mapping):
        days = _coerce_int(value.get("days", 0))
        hours = _coerce_int(value.get("hours", 0))
        minutes = _coerce_int(value.get("minutes", 0))
        seconds = _coerce_int(value.get("seconds", 0))
        parts = (days, hours, minutes, seconds)
        if any(part is None or part < 0 for part in parts):
            return None
        return days * 86_400 + hours * 3_600 + minutes * 60 + seconds

    return _coerce_int(value)


def _seconds_to_duration(value: int) -> dict[str, int]:
    """Convert stored seconds to duration selector defaults."""
    seconds = max(0, int(value))
    hours, remainder = divmod(seconds, 3_600)
    minutes, seconds = divmod(remainder, 60)
    return {
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds,
    }
