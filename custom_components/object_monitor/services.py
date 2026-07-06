"""Service handlers for the Object Monitor integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import homeassistant.helpers.config_validation as cv

from .const import (
    ATTR_CATEGORY,
    ATTR_FRIENDLY_NAME,
    ATTR_OBJECT_LABEL,
    DOMAIN,
    EVENT_TYPE_OFFLINE,
    EVENT_TYPE_RECOVERY,
    SERVICE_CLEAR_ENTITY_STATE,
    SERVICE_RELOAD_MONITORED_ENTITIES,
    SERVICE_SEND_TEST_NOTIFICATION,
)
from .models import NotificationEventType
from .runtime import ObjectMonitorRuntime

ATTR_TEST_EVENT_TYPE = "event_type"

SEND_TEST_NOTIFICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_OBJECT_LABEL): cv.string,
        vol.Optional(ATTR_CATEGORY): vol.Any(None, cv.string),
        vol.Optional(ATTR_TEST_EVENT_TYPE, default=EVENT_TYPE_OFFLINE): vol.In(
            [EVENT_TYPE_OFFLINE, EVENT_TYPE_RECOVERY]
        ),
        vol.Optional(ATTR_ENTITY_ID, default="sensor.object_monitor_test"): cv.string,
        vol.Optional(ATTR_FRIENDLY_NAME, default="Тест Object Monitor"): cv.string,
    }
)

CLEAR_ENTITY_STATE_SCHEMA = vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.string})


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register Object Monitor services."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_TEST_NOTIFICATION,
        _handle_send_test_notification,
        schema=SEND_TEST_NOTIFICATION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RELOAD_MONITORED_ENTITIES,
        _handle_reload_monitored_entities,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_ENTITY_STATE,
        _handle_clear_entity_state,
        schema=CLEAR_ENTITY_STATE_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Remove Object Monitor services."""
    for service in (
        SERVICE_SEND_TEST_NOTIFICATION,
        SERVICE_RELOAD_MONITORED_ENTITIES,
        SERVICE_CLEAR_ENTITY_STATE,
    ):
        hass.services.async_remove(DOMAIN, service)


async def _handle_send_test_notification(call: ServiceCall) -> None:
    """Handle a request to send a test notification."""
    runtime = _get_runtime(call.hass)
    object_label = call.data[ATTR_OBJECT_LABEL].strip().lower()
    raw_category = call.data.get(ATTR_CATEGORY)
    category = raw_category.strip().lower() if raw_category else None

    if object_label not in runtime.config.object_label_set:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="unknown_object_label",
            translation_placeholders={"object_label": object_label},
        )

    if category and category not in runtime.config.category_label_set:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="unknown_category_label",
            translation_placeholders={"category": category},
        )

    result = await runtime.async_send_test_notification(
        object_label=object_label,
        category=category,
        event_type=NotificationEventType(call.data[ATTR_TEST_EVENT_TYPE]),
        entity_id=call.data[ATTR_ENTITY_ID],
        friendly_name=call.data[ATTR_FRIENDLY_NAME],
    )

    if not result.success:
        raise HomeAssistantError(
            f"Test notification was not delivered: {result.reason or 'unknown'}"
        )


async def _handle_reload_monitored_entities(call: ServiceCall) -> None:
    """Handle a request to reload monitored entities."""
    runtime = _get_runtime(call.hass)
    await runtime.async_reload_monitored_entities()


async def _handle_clear_entity_state(call: ServiceCall) -> None:
    """Handle a request to clear one entity's stored monitor state."""
    runtime = _get_runtime(call.hass)
    await runtime.async_clear_entity_state(call.data[ATTR_ENTITY_ID])


def _get_runtime(hass: HomeAssistant) -> ObjectMonitorRuntime:
    """Return the loaded Object Monitor runtime."""
    entries: list[ConfigEntry[ObjectMonitorRuntime]] = hass.config_entries.async_entries(
        DOMAIN
    )
    for entry in entries:
        runtime = getattr(entry, "runtime_data", None)
        if isinstance(runtime, ObjectMonitorRuntime):
            return runtime

    raise HomeAssistantError("Object Monitor is not loaded")
