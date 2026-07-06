"""Base notification provider contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import MonitorNotificationEvent, NotificationResult


class NotificationProvider(ABC):
    """Abstract base class for Object Monitor notification providers."""

    @abstractmethod
    async def async_send(self, event: MonitorNotificationEvent) -> NotificationResult:
        """Send a notification event."""
