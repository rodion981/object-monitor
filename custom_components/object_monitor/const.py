"""Constants for the Object Monitor integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "object_monitor"
NAME: Final = "Object Monitor"

DEFAULT_NAME: Final = NAME
DEFAULT_TIMEOUT_SECONDS: Final = 420
DEFAULT_TIMEOUT: Final = timedelta(seconds=DEFAULT_TIMEOUT_SECONDS)
DEFAULT_DEBUG_LOGGING: Final = False
DEFAULT_HEARTBEAT_INTERVAL_SECONDS: Final = 0

DEFAULT_MONITORING_LABEL: Final = "device_monitoring"

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
CONF_CATEGORY_NAMES: Final = "category_names"
CONF_MONITORING_TIMEOUT: Final = "monitoring_timeout"
CONF_NOTIFICATION_MODE: Final = "notification_mode"
CONF_OBJECT_LABELS: Final = "object_labels"
CONF_DEBUG_LOGGING: Final = "debug_logging"
CONF_NOTIFICATION_PROVIDER: Final = "notification_provider"
CONF_HEARTBEAT_INTERVAL: Final = "heartbeat_interval"

NOTIFICATION_MODE_CATEGORY_ROUTING: Final = "category_routing"
NOTIFICATION_MODE_SINGLE_ROUTING: Final = "single_routing"
NOTIFICATION_MODES: Final[frozenset[str]] = frozenset(
    {
        NOTIFICATION_MODE_CATEGORY_ROUTING,
        NOTIFICATION_MODE_SINGLE_ROUTING,
    }
)
DEFAULT_NOTIFICATION_MODE: Final = NOTIFICATION_MODE_SINGLE_ROUTING

PROVIDER_TELEGRAM: Final = "telegram"
NOTIFICATION_PROVIDERS: Final[frozenset[str]] = frozenset({PROVIDER_TELEGRAM})
DEFAULT_NOTIFICATION_PROVIDER: Final = PROVIDER_TELEGRAM

EVENT_OBJECT_MONITOR: Final = f"{DOMAIN}_event"
EVENT_ENTITY_REGISTRY_UPDATED: Final = "entity_registry_updated"
EVENT_TYPE_OFFLINE: Final = "offline"
EVENT_TYPE_RECOVERY: Final = "recovery"

STATE_UNAVAILABLE: Final = "unavailable"
STATE_UNKNOWN: Final = "unknown"

STORAGE_KEY: Final = DOMAIN
STORAGE_VERSION: Final = 1
STORAGE_MINOR_VERSION: Final = 1

SCRIPT_DOMAIN: Final = "script"
TELEGRAM_SCRIPT_PREFIX: Final = "tg"

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
