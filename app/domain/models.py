from enum import StrEnum
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

class Status(StrEnum):
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class Severity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class Source(StrEnum):
    operator = "operator"
    monitoring = "monitoring"
    partner = "partner"
    system = "system"

class EventType(StrEnum):
    CREATED = "CREATED"
    SIGNAL_RECEIVED = "SIGNAL_RECEIVED"
    STATUS_CHANGED = "STATUS_CHANGED"
    COMMENT_ADDED = "COMMENT_ADDED"
    NOTIFICATION_SENT = "NOTIFICATION_SENT"
    AUTO_RESOLVED = "AUTO_RESOLVED"

@dataclass(frozen=True, slots=True)
class Incident:
    id: int | None
    title: str
    description: str
    status: Status
    severity: Severity
    source: Source
    fingerprint: str
    target: str
    created_at: datetime
    updated_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    last_seen_at: datetime | None = None
    occurrence_count: int = 1
    version: int = 1

    @staticmethod
    def new(
        title: str,
        description: str,
        severity: Severity,
        source: Source,
        fingerprint: str,
        target: str,
    ) -> "Incident":
        now = datetime.now(timezone.utc)
        return Incident(
            id=None,
            title=title,
            description=description,
            status=Status.NEW,
            severity=severity,
            source=source,
            fingerprint=fingerprint,
            target=target,
            created_at=now,
            updated_at=now,
            last_seen_at=now,
        )

@dataclass(frozen=True, slots=True)
class IncidentEvent:
    id: int | None
    incident_id: int
    event_type: EventType
    payload: dict[str, Any]
    created_at: datetime

    @staticmethod
    def new(incident_id: int, event_type: EventType, payload: dict[str, Any]) -> "IncidentEvent":
        return IncidentEvent(
            id=None,
            incident_id=incident_id,
            event_type=event_type,
            payload=payload,
            created_at=datetime.now(timezone.utc),
        )
