from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship
from sqlalchemy import String, Enum, DateTime, func, Integer, ForeignKey, JSON, Index
from app.domain.models import (
    EventType,
    Incident,
    IncidentEvent,
    IncidentNotification,
    NotificationChannel,
    NotificationStatus,
    Severity,
    Source,
    Status,
)
from datetime import datetime
from typing import Any

Base = declarative_base()

class IncidentORM(Base):
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    status: Mapped[Status] = mapped_column(Enum(Status), nullable=False, default=Status.NEW)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), nullable=False)
    source: Mapped[Source] = mapped_column(Enum(Source), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    target: Mapped[str] = mapped_column(String(300), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    events: Mapped[list["IncidentEventORM"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["IncidentNotificationORM"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_incidents_open_fingerprint", "fingerprint", "status"),
    )

    def to_domain(self) -> Incident:
        return Incident(
            id=self.id,
            title=self.title,
            description=self.description,
            status=self.status,
            severity=self.severity,
            source=self.source,
            fingerprint=self.fingerprint,
            target=self.target,
            created_at=self.created_at,
            updated_at=self.updated_at,
            resolved_at=self.resolved_at,
            closed_at=self.closed_at,
            last_seen_at=self.last_seen_at,
            occurrence_count=self.occurrence_count,
            version=self.version,
        )

    def etag(self) -> str:
        return f'W/"incident-{self.id}-v{self.version}"'

class IncidentEventORM(Base):
    __tablename__ = "incident_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), nullable=False, index=True)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    incident: Mapped[IncidentORM] = relationship(back_populates="events")

    def to_domain(self) -> IncidentEvent:
        return IncidentEvent(
            id=self.id,
            incident_id=self.incident_id,
            event_type=self.event_type,
            payload=self.payload,
            created_at=self.created_at,
        )

class IncidentNotificationORM(Base):
    __tablename__ = "incident_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), nullable=False, index=True)
    notification_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel), nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus), nullable=False)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    incident: Mapped[IncidentORM] = relationship(back_populates="notifications")

    def to_domain(self) -> IncidentNotification:
        return IncidentNotification(
            id=self.id,
            incident_id=self.incident_id,
            notification_id=self.notification_id,
            channel=self.channel,
            status=self.status,
            error=self.error,
            created_at=self.created_at,
            sent_at=self.sent_at,
        )
