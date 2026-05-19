from typing import Any

from app.adapters.repo import IncidentsRepo
from app.domain.models import EventType, Incident, IncidentEvent, Severity, Source, Status
from app.domain.rules import ensure_transition


def create(
    repo: IncidentsRepo,
    title: str,
    description: str,
    severity: Severity,
    source: Source,
    fingerprint: str,
    target: str,
) -> Incident:
    incident = repo.add(
        Incident.new(
            title=title,
            description=description,
            severity=severity,
            source=source,
            fingerprint=fingerprint,
            target=target,
        )
    )
    if incident.id is None:
        raise RuntimeError("incident was not persisted")
    repo.add_event(
        incident.id,
        EventType.CREATED,
        {
            "title": title,
            "severity": severity.value,
            "source": source.value,
            "fingerprint": fingerprint,
            "target": target,
        },
    )
    return incident


def ingest_signal(
    repo: IncidentsRepo,
    title: str,
    description: str,
    severity: Severity,
    source: Source,
    fingerprint: str,
    target: str,
) -> tuple[Incident, bool]:
    existing = repo.find_open_by_fingerprint(fingerprint)
    payload: dict[str, Any] = {
        "title": title,
        "description": description,
        "severity": severity.value,
        "source": source.value,
        "fingerprint": fingerprint,
        "target": target,
    }
    if existing and existing.id is not None:
        return repo.mark_seen(existing.id, payload), False
    return create(repo, title, description, severity, source, fingerprint, target), True


def list_(
    repo: IncidentsRepo,
    status: Status | None,
    source: Source | None,
    limit: int,
    offset: int,
):
    return repo.list(status, source, limit, offset)


def get(repo: IncidentsRepo, id_: int) -> Incident:
    incident = repo.get(id_)
    if not incident:
        raise KeyError("not found")
    return incident


def update(
    repo: IncidentsRepo,
    id_: int,
    new_status: Status | None,
    description_append: str | None,
    etag: str | None = None,
) -> Incident:
    current = get(repo, id_)
    if new_status is not None:
        ensure_transition(current.status, new_status)
    return repo.update(id_, new_status, description_append, etag)


def ack(repo: IncidentsRepo, id_: int, etag: str | None = None) -> Incident:
    return update(repo, id_, Status.ACKNOWLEDGED, None, etag)


def resolve(
    repo: IncidentsRepo,
    id_: int,
    comment: str | None = None,
    etag: str | None = None,
) -> Incident:
    return update(repo, id_, Status.RESOLVED, comment, etag)


def close(repo: IncidentsRepo, id_: int, etag: str | None = None) -> Incident:
    return update(repo, id_, Status.CLOSED, None, etag)


def add_comment(repo: IncidentsRepo, id_: int, comment: str) -> Incident:
    get(repo, id_)
    return repo.update(id_, None, comment)


def list_events(repo: IncidentsRepo, id_: int) -> list[IncidentEvent]:
    get(repo, id_)
    return repo.list_events(id_)
