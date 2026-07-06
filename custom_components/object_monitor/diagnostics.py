"""Diagnostics support for the Object Monitor integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .runtime import ObjectMonitorRuntime

type ObjectMonitorConfigEntry = ConfigEntry[ObjectMonitorRuntime]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: ObjectMonitorConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime = config_entry.runtime_data

    return {
        "entry": {
            "entry_id": config_entry.entry_id,
            "title": config_entry.title,
            "version": config_entry.version,
            "minor_version": config_entry.minor_version,
        },
        "runtime": runtime.diagnostics(),
    }
