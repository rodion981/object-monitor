"""Object Monitor integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .runtime import ObjectMonitorRuntime
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

type ObjectMonitorConfigEntry = ConfigEntry[ObjectMonitorRuntime]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ObjectMonitorConfigEntry,
) -> bool:
    """Set up Object Monitor from a config entry."""
    await async_setup_services(hass)

    runtime = ObjectMonitorRuntime(hass, entry)
    await runtime.async_start()

    entry.runtime_data = runtime
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _LOGGER.debug("Object Monitor config entry %s set up", entry.entry_id)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ObjectMonitorConfigEntry,
) -> bool:
    """Unload an Object Monitor config entry."""
    runtime = entry.runtime_data
    await runtime.async_stop()
    await async_unload_services(hass)

    _LOGGER.debug("Object Monitor config entry %s unloaded", entry.entry_id)
    return True


async def _async_update_listener(
    hass: HomeAssistant,
    entry: ObjectMonitorConfigEntry,
) -> None:
    """Reload Object Monitor when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
