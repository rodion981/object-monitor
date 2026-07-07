"""Constants for the Object Monitor integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "object_monitor"
NAME: Final = "Object Event Monitor"

DEFAULT_NAME: Final = NAME
DEFAULT_TIMEOUT_SECONDS: Final = 420
DEFAULT_TIMEOUT: Final = timedelta(seconds=DEFAULT_TIMEOUT_SECONDS)
DEFAULT_DEBUG_LOGGING: Final = False
DEFAULT_HEARTBEAT_INTERVAL_SECONDS: Final = 0

DEFAULT_MONITORING_LABEL: Final = "device_monitoring"
SECURITY_SYSTEM_LABEL: Final = "security_system"
ON_OFF_MONITOR_LABEL: Final = "state_monitor"
DEFAULT_ON_STATE_VALUES: Final[tuple[str, ...]] = ("on",)
DEFAULT_OFF_STATE_VALUES: Final[tuple[str, ...]] = ("off",)

CATEGORY_SECURITY: Final = "security"
CATEGORY_LIGHT: Final = "light"
CATEGORY_CLIMATE: Final = "climate"
DEFAULT_CATEGORY_LABELS: Final[tuple[str, ...]] = (
    CATEGORY_SECURITY,
    CATEGORY_LIGHT,
    CATEGORY_CLIMATE,
)

CONF_MONITORING_LABEL: Final = "monitoring_label"
CONF_CATEGORY_LABELS: Final = "category_labels"
CONF_OBJECT_NAMES: Final = "object_names"
CONF_ON_STATE_VALUES: Final = "on_state_values"
CONF_OFF_STATE_VALUES: Final = "off_state_values"
CONF_CATEGORY_NAMES: Final = "category_names"
CONF_MONITORING_TIMEOUT: Final = "monitoring_timeout"
CONF_OBJECT_LABELS: Final = "object_labels"
CONF_DEBUG_LOGGING: Final = "debug_logging"
CONF_HEARTBEAT_INTERVAL: Final = "heartbeat_interval"

EVENT_OBJECT_MONITOR_OFFLINE: Final = f"{DOMAIN}_offline"
EVENT_OBJECT_MONITOR_RECOVERY: Final = f"{DOMAIN}_recovery"
EVENT_OBJECT_MONITOR_SECURITY_STATE: Final = f"{DOMAIN}_security_state"
EVENT_OBJECT_MONITOR_ON_OFF_STATE: Final = f"{DOMAIN}_on_off_state"
EVENT_ENTITY_REGISTRY_UPDATED: Final = "entity_registry_updated"
EVENT_TYPE_OFFLINE: Final = "offline"
EVENT_TYPE_RECOVERY: Final = "recovery"
EVENT_TYPE_SECURITY_STATE: Final = "security_state"
EVENT_TYPE_ON_OFF_STATE: Final = "on_off_state"

ALARM_CONTROL_PANEL_DOMAIN: Final = "alarm_control_panel"

STATE_UNAVAILABLE: Final = "unavailable"
STATE_UNKNOWN: Final = "unknown"

STORAGE_KEY: Final = DOMAIN
STORAGE_VERSION: Final = 1
STORAGE_MINOR_VERSION: Final = 1

ATTR_EVENT_TYPE: Final = "event_type"
ATTR_ENTITY_ID: Final = "entity_id"
ATTR_FRIENDLY_NAME: Final = "friendly_name"
ATTR_OBJECT_LABEL: Final = "object_label"
ATTR_CATEGORY: Final = "category"
ATTR_UNAVAILABLE_SINCE: Final = "unavailable_since"
ATTR_NOTIFIED_AT: Final = "notified_at"

SERVICE_SEND_TEST_NOTIFICATION: Final = "send_test_notification"
SERVICE_RELOAD_MONITORED_ENTITIES: Final = "reload_monitored_entities"
SERVICE_CLEAR_ENTITY_STATE: Final = "clear_entity_state"
