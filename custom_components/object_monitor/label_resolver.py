"""Resolve Object Monitor metadata from Home Assistant labels."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from .models import EntityLabels, LabelResolutionStatus, MonitorConfig

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class LabelResolver:
    """Resolve monitored object and category labels for entities."""

    def __init__(self, hass: HomeAssistant, config: MonitorConfig) -> None:
        """Initialize the label resolver."""
        self._hass = hass
        self._config = config

    @property
    def object_labels(self) -> frozenset[str]:
        """Return configured object labels."""
        return self._config.object_label_set

    @property
    def category_labels(self) -> frozenset[str]:
        """Return configured category labels."""
        return self._config.category_label_set

    def resolve_entity(self, entity_id: str) -> EntityLabels:
        """Resolve monitoring labels for one entity ID."""
        from homeassistant.helpers import entity_registry as er

        registry = er.async_get(self._hass)
        entry = registry.async_get(entity_id)

        if entry is None:
            return EntityLabels(
                entity_id=entity_id,
                labels=frozenset(),
                status=LabelResolutionStatus.NOT_MONITORED,
                reason="entity_not_registered",
            )

        return self.resolve_from_labels(entity_id, _entry_labels(entry))

    def resolve_from_labels(
        self,
        entity_id: str,
        labels: Iterable[str],
    ) -> EntityLabels:
        """Resolve monitoring metadata from raw labels."""
        normalized_labels = _normalize_labels(labels)

        if self._config.monitoring_label not in normalized_labels:
            return EntityLabels(
                entity_id=entity_id,
                labels=normalized_labels,
                status=LabelResolutionStatus.NOT_MONITORED,
                reason="missing_monitoring_label",
            )

        object_matches = sorted(normalized_labels & self.object_labels)
        if not object_matches:
            return EntityLabels(
                entity_id=entity_id,
                labels=normalized_labels,
                status=LabelResolutionStatus.MISSING_OBJECT,
                reason="missing_object_label",
            )

        if len(object_matches) > 1:
            return EntityLabels(
                entity_id=entity_id,
                labels=normalized_labels,
                status=LabelResolutionStatus.MULTIPLE_OBJECTS,
                reason=f"multiple_object_labels: {', '.join(object_matches)}",
            )

        category_matches = sorted(normalized_labels & self.category_labels)
        category = category_matches[0] if len(category_matches) == 1 else None
        category_error = (
            "multiple_category_labels" if len(category_matches) > 1 else None
        )

        return EntityLabels(
            entity_id=entity_id,
            labels=normalized_labels,
            status=LabelResolutionStatus.MONITORED,
            object_label=object_matches[0],
            category=category,
            category_error=category_error,
        )

    def resolve_all_monitored(self) -> dict[str, EntityLabels]:
        """Resolve all currently registered monitored entities."""
        from homeassistant.helpers import entity_registry as er

        registry = er.async_get(self._hass)
        resolved: dict[str, EntityLabels] = {}

        for entity_id, entry in registry.entities.items():
            labels = self.resolve_from_labels(entity_id, _entry_labels(entry))
            if labels.is_monitored:
                resolved[entity_id] = labels

        return resolved


def _entry_labels(entry: Any) -> frozenset[str]:
    """Return labels from an entity registry entry."""
    return _normalize_labels(getattr(entry, "labels", set()))


def _normalize_labels(labels: Iterable[str]) -> frozenset[str]:
    """Normalize Home Assistant label IDs for stable matching."""
    return frozenset(label.strip().lower() for label in labels if label.strip())
