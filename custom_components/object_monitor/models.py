"""Data models for the Object Monitor integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from .const import (
    DEFAULT_DEBUG_LOGGING,
    DEFAULT_CATEGORY_LABELS,
    DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
    DEFAULT_MONITORING_LABEL,
    DEFAULT_TIMEOUT_SECONDS,
    EVENT_TYPE_ON_OFF_STATE,
    EVENT_TYPE_SECURITY_STATE,
)


class NotificationEventType(StrEnum):
    """Supported monitor notification event types."""

    OFFLINE = "offline"
    RECOVERY = "recovery"


class SecuritySystemState(StrEnum):
    """Supported security system states."""

    DISARMED = "disarmed"
    ARMED_HOME = "armed_home"
    ARMED_AWAY = "armed_away"
    ARMED_NIGHT = "armed_night"
    ARMED_VACATION = "armed_vacation"
    ARMING = "arming"
    PENDING = "pending"
    TRIGGERED = "triggered"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class LabelResolutionStatus(StrEnum):
    """Result status for label resolution."""

    MONITORED = "monitored"
    NOT_MONITORED = "not_monitored"
    MISSING_OBJECT = "missing_object"
    MULTIPLE_OBJECTS = "multiple_objects"
    MULTIPLE_CATEGORIES = "multiple_categories"
    MULTIPLE_TIMEOUTS = "multiple_timeouts"


@dataclass(slots=True, frozen=True)
class MonitorConfig:
    """Runtime configuration for a loaded Object Monitor config entry."""

    monitoring_label: str = DEFAULT_MONITORING_LABEL
    category_labels: tuple[str, ...] = DEFAULT_CATEGORY_LABELS
    monitoring_timeout: int = DEFAULT_TIMEOUT_SECONDS
    object_labels: tuple[str, ...] = ()
    object_names: dict[str, str] = field(default_factory=dict)
    category_names: dict[str, str] = field(default_factory=dict)
    debug_logging: bool = DEFAULT_DEBUG_LOGGING
    heartbeat_interval: int = DEFAULT_HEARTBEAT_INTERVAL_SECONDS

    @property
    def object_label_set(self) -> frozenset[str]:
        """Return configured object labels as a set for fast lookups."""
        return frozenset(self.object_labels)

    @property
    def category_label_set(self) -> frozenset[str]:
        """Return configured category labels as a set for fast lookups."""
        return frozenset(self.category_labels)

    def object_display_name(self, label: str) -> str:
        """Return a display name for an object label."""
        return self.object_names.get(label, label)

    def category_display_name(self, label: str) -> str:
        """Return a display name for a category label."""
        return self.category_names.get(label, label)


@dataclass(slots=True, frozen=True)
class EntityLabels:
    """Resolved monitoring labels for one Home Assistant entity."""

    entity_id: str
    labels: frozenset[str]
    status: LabelResolutionStatus
    object_label: str | None = None
    category: str | None = None
    timeout_seconds: int | None = None
    reason: str | None = None
    category_error: str | None = None

    @property
    def is_monitored(self) -> bool:
        """Return true when this entity is valid for monitoring."""
        return self.status is LabelResolutionStatus.MONITORED


@dataclass(slots=True)
class MonitoredEntity:
    """In-memory monitoring state for a single entity."""

    entity_id: str
    object_label: str
    category: str | None
    friendly_name: str
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    unavailable_since: datetime | None = None
    offline_confirmed: bool = False
    notified_offline: bool = False
    last_notification_type: NotificationEventType | None = None
    last_notified_at: datetime | None = None

    @property
    def is_pending(self) -> bool:
        """Return true when the entity is inside the grace period."""
        return self.unavailable_since is not None and not self.offline_confirmed

    @property
    def is_offline(self) -> bool:
        """Return true when the entity has been confirmed offline."""
        return self.offline_confirmed


@dataclass(slots=True, frozen=True)
class NotificationEvent:
    """Provider-neutral event emitted by the monitor."""

    event_type: NotificationEventType
    entity_id: str
    friendly_name: str
    object_label: str
    category: str | None
    unavailable_since: datetime | None = None
    notified_at: datetime | None = None
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

    def as_event_data(self) -> dict[str, Any]:
        """Return serializable data suitable for the Home Assistant event bus."""
        return {
            "event_type": self.event_type.value,
            "entity_id": self.entity_id,
            "friendly_name": self.friendly_name,
            "object_label": self.object_label,
            "category": self.category,
            "unavailable_since": self.unavailable_since.isoformat()
            if self.unavailable_since
            else None,
            "notified_at": self.notified_at.isoformat() if self.notified_at else None,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(slots=True, frozen=True)
class SecurityStateEvent:
    """Provider-neutral event emitted by security system monitoring."""

    entity_id: str
    friendly_name: str
    object_label: str
    previous_state: SecuritySystemState | None
    state: SecuritySystemState
    category: str = "security"
    notified_at: datetime | None = None

    def as_event_data(self) -> dict[str, Any]:
        """Return serializable data suitable for the Home Assistant event bus."""
        return {
            "event_type": EVENT_TYPE_SECURITY_STATE,
            "entity_id": self.entity_id,
            "friendly_name": self.friendly_name,
            "object_label": self.object_label,
            "category": self.category,
            "previous_state": self.previous_state.value
            if self.previous_state
            else None,
            "state": self.state.value,
            "notified_at": self.notified_at.isoformat() if self.notified_at else None,
        }


@dataclass(slots=True, frozen=True)
class OnOffStateEvent:
    """Provider-neutral event emitted by on/off state monitoring."""

    entity_id: str
    friendly_name: str
    object_label: str
    category: str | None
    previous_state: str
    state: str
    notified_at: datetime | None = None

    def as_event_data(self) -> dict[str, Any]:
        """Return serializable data suitable for the Home Assistant event bus."""
        return {
            "event_type": EVENT_TYPE_ON_OFF_STATE,
            "entity_id": self.entity_id,
            "friendly_name": self.friendly_name,
            "object_label": self.object_label,
            "category": self.category,
            "previous_state": self.previous_state,
            "state": self.state,
            "notified_at": self.notified_at.isoformat() if self.notified_at else None,
        }


MonitorNotificationEvent = NotificationEvent | SecurityStateEvent | OnOffStateEvent


@dataclass(slots=True, frozen=True)
class NotificationResult:
    """Result returned by a notification provider."""

    success: bool
    target: str | None = None
    reason: str | None = None


@dataclass(slots=True, frozen=True)
class StoredEntityState:
    """Persistent monitor state for one entity."""

    entity_id: str
    object_label: str
    category: str | None
    friendly_name: str
    timeout_seconds: int
    unavailable_since: datetime | None
    offline_confirmed: bool
    notified_offline: bool
    last_notification_type: NotificationEventType | None
    last_notified_at: datetime | None

    @classmethod
    def from_monitored_entity(cls, entity: MonitoredEntity) -> StoredEntityState:
        """Create persisted state from an in-memory monitored entity."""
        return cls(
            entity_id=entity.entity_id,
            object_label=entity.object_label,
            category=entity.category,
            friendly_name=entity.friendly_name,
            timeout_seconds=entity.timeout_seconds,
            unavailable_since=entity.unavailable_since,
            offline_confirmed=entity.offline_confirmed,
            notified_offline=entity.notified_offline,
            last_notification_type=entity.last_notification_type,
            last_notified_at=entity.last_notified_at,
        )

    def to_json(self) -> dict[str, Any]:
        """Return JSON-serializable stored state."""
        return {
            "entity_id": self.entity_id,
            "object_label": self.object_label,
            "category": self.category,
            "friendly_name": self.friendly_name,
            "timeout_seconds": self.timeout_seconds,
            "unavailable_since": self.unavailable_since.isoformat()
            if self.unavailable_since
            else None,
            "offline_confirmed": self.offline_confirmed,
            "notified_offline": self.notified_offline,
            "last_notification_type": self.last_notification_type.value
            if self.last_notification_type
            else None,
            "last_notified_at": self.last_notified_at.isoformat()
            if self.last_notified_at
            else None,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> StoredEntityState:
        """Create stored state from JSON data."""
        last_type = data.get("last_notification_type")
        return cls(
            entity_id=data["entity_id"],
            object_label=data["object_label"],
            category=data.get("category"),
            friendly_name=data.get("friendly_name") or data["entity_id"],
            timeout_seconds=int(data.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)),
            unavailable_since=_parse_datetime(data.get("unavailable_since")),
            offline_confirmed=bool(
                data.get("offline_confirmed", data.get("notified_offline", False))
            ),
            notified_offline=bool(data.get("notified_offline", False)),
            last_notification_type=NotificationEventType(last_type)
            if last_type
            else None,
            last_notified_at=_parse_datetime(data.get("last_notified_at")),
        )


@dataclass(slots=True, frozen=True)
class StoredMonitorState:
    """Persistent state for the Object Monitor integration."""

    entities: dict[str, StoredEntityState] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        """Return JSON-serializable monitor state."""
        return {
            "entities": {
                entity_id: entity.to_json()
                for entity_id, entity in self.entities.items()
            }
        }

    @classmethod
    def from_json(cls, data: dict[str, Any] | None) -> StoredMonitorState:
        """Create monitor state from JSON data."""
        if not data:
            return cls()

        raw_entities = data.get("entities", {})
        entities: dict[str, StoredEntityState] = {}
        for entity_id, raw_entity in raw_entities.items():
            if isinstance(raw_entity, dict):
                entities[entity_id] = StoredEntityState.from_json(raw_entity)

        return cls(entities=entities)


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse an ISO 8601 datetime value from storage."""
    if not value:
        return None
    return datetime.fromisoformat(value)
