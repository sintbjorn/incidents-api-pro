from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.adapters.orm import IncidentEventORM, IncidentORM
from app.domain.models import EventType, Incident, IncidentEvent, Source, Status


OPEN_STATUSES = (Status.NEW, Status.ACKNOWLEDGED, Status.IN_PROGRESS, Status.RESOLVED)


class IncidentsRepo(Protocol):
    def add(self, incident: Incident) -> Incident: ...
    def get(self, id_: int) -> Incident | None: ...
    def get_row(self, id_: int) -> IncidentORM | None: ...
    def list(
        self, status: Status | None, source: Source | None, limit: int, offset: int
    ) -> tuple[list[Incident], int]: ...
    def find_open_by_fingerprint(self, fingerprint: str) -> Incident | None: ...
    def mark_seen(self, id_: int, payload: dict[str, Any]) -> Incident: ...
    def update(
        self,
        id_: int,
        new_status: Status | None,
        description_append: str | None,
        etag: str | None = None,
    ) -> Incident: ...
    def add_event(
        self, incident_id: int, event_type: EventType, payload: dict[str, Any]
    ) -> IncidentEvent: ...
    def list_events(self, incident_id: int) -> list[IncidentEvent]: ...


class SqlAlchemyIncidentsRepo:
    def __init__(self, session: Session):
        self.s = session

    def add(self, incident: Incident) -> Incident:
        row = IncidentORM(
            title=incident.title,
            description=incident.description,
            status=incident.status,
            severity=incident.severity,
            source=incident.source,
            fingerprint=incident.fingerprint,
            target=incident.target,
            last_seen_at=incident.last_seen_at,
            occurrence_count=incident.occurrence_count,
            version=incident.version,
        )
        self.s.add(row)
        self.s.flush()
        self.s.refresh(row)
        return row.to_domain()

    def get(self, id_: int) -> Incident | None:
        row = self.get_row(id_)
        return row.to_domain() if row else None

    def get_row(self, id_: int) -> IncidentORM | None:
        return self.s.get(IncidentORM, id_)

    def list(self, status, source, limit, offset):
        q = self.s.query(IncidentORM)
        if status:
            q = q.filter(IncidentORM.status == status)
        if source:
            q = q.filter(IncidentORM.source == source)
        total = q.count()
        items = (
            q.order_by(IncidentORM.created_at.desc(), IncidentORM.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [row.to_domain() for row in items], total

    def find_open_by_fingerprint(self, fingerprint: str) -> Incident | None:
        row = (
            self.s.query(IncidentORM)
            .filter(
                IncidentORM.fingerprint == fingerprint,
                IncidentORM.status.in_(OPEN_STATUSES),
            )
            .order_by(IncidentORM.created_at.desc(), IncidentORM.id.desc())
            .first()
        )
        return row.to_domain() if row else None

    def mark_seen(self, id_: int, payload: dict[str, Any]) -> Incident:
        row = self._require_row(id_)
        now = datetime.now(timezone.utc)
        row.last_seen_at = now
        row.updated_at = now
        row.occurrence_count += 1
        row.version += 1
        self.s.add(row)
        self.add_event(id_, EventType.SIGNAL_RECEIVED, payload)
        self.s.flush()
        self.s.refresh(row)
        return row.to_domain()

    def update(
        self,
        id_: int,
        new_status: Status | None,
        description_append: str | None,
        etag: str | None = None,
    ) -> Incident:
        row = self._require_row(id_)
        if etag and etag != row.etag():
            raise PermissionError("etag mismatch")

        old_status = row.status
        changed = False
        now = datetime.now(timezone.utc)

        if new_status is not None and new_status != row.status:
            row.status = new_status
            row.resolved_at = now if new_status == Status.RESOLVED else row.resolved_at
            row.closed_at = now if new_status == Status.CLOSED else row.closed_at
            self.add_event(
                id_,
                EventType.STATUS_CHANGED,
                {"from_status": old_status.value, "to_status": new_status.value},
            )
            changed = True

        if description_append:
            row.description = (row.description.rstrip() + "\n" + description_append.strip()).strip()
            self.add_event(id_, EventType.COMMENT_ADDED, {"comment": description_append})
            changed = True

        if changed:
            row.updated_at = now
            row.version += 1
            self.s.add(row)

        self.s.flush()
        self.s.refresh(row)
        return row.to_domain()

    def add_event(
        self, incident_id: int, event_type: EventType, payload: dict[str, Any]
    ) -> IncidentEvent:
        row = IncidentEventORM(
            incident_id=incident_id,
            event_type=event_type,
            payload=payload,
        )
        self.s.add(row)
        self.s.flush()
        self.s.refresh(row)
        return row.to_domain()

    def list_events(self, incident_id: int) -> list[IncidentEvent]:
        rows = (
            self.s.query(IncidentEventORM)
            .filter(IncidentEventORM.incident_id == incident_id)
            .order_by(IncidentEventORM.created_at.asc(), IncidentEventORM.id.asc())
            .all()
        )
        return [row.to_domain() for row in rows]

    def _require_row(self, id_: int) -> IncidentORM:
        row = self.get_row(id_)
        if not row:
            raise KeyError("not found")
        return row
