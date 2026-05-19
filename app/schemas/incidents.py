from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import (
    EventType,
    NotificationChannel,
    NotificationStatus,
    Severity,
    Source,
    Status,
)


class IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=2000)
    severity: Severity = Severity.WARNING
    source: Source
    fingerprint: str = Field(min_length=1, max_length=500)
    target: str = Field(min_length=1, max_length=300)


class SignalIn(IncidentCreate):
    pass


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: Status
    severity: Severity
    source: Source
    fingerprint: str
    target: str
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None
    last_seen_at: datetime
    occurrence_count: int
    version: int


class IncidentUpdate(BaseModel):
    status: Status | None = None
    description_append: str | None = Field(default=None, min_length=1, max_length=2000)


class CommentCreate(BaseModel):
    comment: str = Field(min_length=1, max_length=2000)


class ResolveCreate(BaseModel):
    comment: str | None = Field(default=None, min_length=1, max_length=2000)


class IncidentEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    event_type: EventType
    payload: dict[str, Any]
    created_at: datetime


class IncidentNotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    channel: NotificationChannel
    status: NotificationStatus
    notification_id: str | None
    error: str | None
    created_at: datetime
    sent_at: datetime | None
