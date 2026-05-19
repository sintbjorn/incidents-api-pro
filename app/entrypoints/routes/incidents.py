from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Response
from prometheus_client import Counter

from app.adapters.db import session_dep
from app.adapters.repo import SqlAlchemyIncidentsRepo
from app.domain.models import Source, Status
from app.schemas.incidents import (
    CommentCreate,
    IncidentCreate,
    IncidentEventOut,
    IncidentOut,
    IncidentUpdate,
    ResolveCreate,
    SignalIn,
)
from app.services import incidents as svc

router = APIRouter()

INCIDENTS_CREATED = Counter(
    "incidents_created_total",
    "Incidents created by severity and source",
    ("severity", "source"),
)
SIGNALS_DEDUPED = Counter(
    "incident_signals_deduplicated_total",
    "Signals deduplicated into an existing open incident",
    ("severity", "source"),
)
STATUS_TRANSITIONS = Counter(
    "incident_status_transitions_total",
    "Incident status transitions",
    ("from_status", "to_status"),
)


def get_repo(s=Depends(session_dep)):
    return SqlAlchemyIncidentsRepo(s)


def _set_etag(response: Response, incident: IncidentOut) -> None:
    response.headers["ETag"] = f'W/"incident-{incident.id}-v{incident.version}"'


def _raise_api_error(exc: Exception) -> None:
    if isinstance(exc, KeyError):
        raise HTTPException(404, "Incident not found") from exc
    if isinstance(exc, ValueError):
        raise HTTPException(409, str(exc)) from exc
    if isinstance(exc, PermissionError):
        raise HTTPException(412, "Precondition Failed (ETag mismatch)") from exc
    raise exc


@router.post("/incidents", response_model=IncidentOut, status_code=201)
def create_incident(payload: IncidentCreate, response: Response, repo=Depends(get_repo)):
    incident = svc.create(
        repo,
        payload.title,
        payload.description,
        payload.severity,
        payload.source,
        payload.fingerprint,
        payload.target,
    )
    INCIDENTS_CREATED.labels(payload.severity.value, payload.source.value).inc()
    out = IncidentOut.model_validate(incident)
    _set_etag(response, out)
    return out


@router.post("/signals", response_model=IncidentOut, status_code=202)
def ingest_signal(payload: SignalIn, response: Response, repo=Depends(get_repo)):
    incident, created = svc.ingest_signal(
        repo,
        payload.title,
        payload.description,
        payload.severity,
        payload.source,
        payload.fingerprint,
        payload.target,
    )
    if created:
        response.status_code = 201
        INCIDENTS_CREATED.labels(payload.severity.value, payload.source.value).inc()
    else:
        SIGNALS_DEDUPED.labels(payload.severity.value, payload.source.value).inc()
    out = IncidentOut.model_validate(incident)
    _set_etag(response, out)
    return out


@router.get("/incidents", response_model=list[IncidentOut])
def list_incidents(
    response: Response,
    status: Status | None = Query(None),
    source: Source | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    repo=Depends(get_repo),
):
    items, total = svc.list_(repo, status, source, limit, offset)
    response.headers["X-Total-Count"] = str(total)
    if items:
        response.headers["Content-Range"] = f"incidents {offset}-{offset + len(items) - 1}/{total}"
    else:
        response.headers["Content-Range"] = f"incidents */{total}"
    return [IncidentOut.model_validate(item) for item in items]


@router.get("/incidents/{incident_id}", response_model=IncidentOut)
def get_incident(incident_id: int, response: Response, repo=Depends(get_repo)):
    try:
        out = IncidentOut.model_validate(svc.get(repo, incident_id))
        _set_etag(response, out)
        return out
    except Exception as exc:
        _raise_api_error(exc)


@router.patch("/incidents/{incident_id}", response_model=IncidentOut)
def update_incident(
    incident_id: int,
    payload: IncidentUpdate,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
    repo=Depends(get_repo),
):
    try:
        before = svc.get(repo, incident_id)
        incident = svc.update(
            repo,
            incident_id,
            payload.status,
            payload.description_append,
            etag=if_match,
        )
        if payload.status is not None and payload.status != before.status:
            STATUS_TRANSITIONS.labels(before.status.value, payload.status.value).inc()
        out = IncidentOut.model_validate(incident)
        _set_etag(response, out)
        return out
    except Exception as exc:
        _raise_api_error(exc)


@router.patch("/incidents/{incident_id}/status", response_model=IncidentOut)
def update_status(
    incident_id: int,
    payload: IncidentUpdate,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
    repo=Depends(get_repo),
):
    if payload.status is None:
        raise HTTPException(422, "status is required")
    return update_incident(incident_id, payload, response, if_match, repo)


@router.post("/incidents/{incident_id}/ack", response_model=IncidentOut)
def acknowledge_incident(
    incident_id: int,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
    repo=Depends(get_repo),
):
    try:
        before = svc.get(repo, incident_id)
        incident = svc.ack(repo, incident_id, etag=if_match)
        STATUS_TRANSITIONS.labels(before.status.value, incident.status.value).inc()
        out = IncidentOut.model_validate(incident)
        _set_etag(response, out)
        return out
    except Exception as exc:
        _raise_api_error(exc)


@router.post("/incidents/{incident_id}/resolve", response_model=IncidentOut)
def resolve_incident(
    incident_id: int,
    response: Response,
    payload: ResolveCreate = Body(default_factory=ResolveCreate),
    if_match: str | None = Header(default=None, alias="If-Match"),
    repo=Depends(get_repo),
):
    try:
        before = svc.get(repo, incident_id)
        incident = svc.resolve(repo, incident_id, payload.comment, etag=if_match)
        STATUS_TRANSITIONS.labels(before.status.value, incident.status.value).inc()
        out = IncidentOut.model_validate(incident)
        _set_etag(response, out)
        return out
    except Exception as exc:
        _raise_api_error(exc)


@router.post("/incidents/{incident_id}/close", response_model=IncidentOut)
def close_incident(
    incident_id: int,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
    repo=Depends(get_repo),
):
    try:
        before = svc.get(repo, incident_id)
        incident = svc.close(repo, incident_id, etag=if_match)
        STATUS_TRANSITIONS.labels(before.status.value, incident.status.value).inc()
        out = IncidentOut.model_validate(incident)
        _set_etag(response, out)
        return out
    except Exception as exc:
        _raise_api_error(exc)


@router.post("/incidents/{incident_id}/comments", response_model=IncidentOut)
def add_comment(incident_id: int, payload: CommentCreate, repo=Depends(get_repo)):
    try:
        return IncidentOut.model_validate(svc.add_comment(repo, incident_id, payload.comment))
    except Exception as exc:
        _raise_api_error(exc)


@router.get("/incidents/{incident_id}/events", response_model=list[IncidentEventOut])
def list_events(incident_id: int, repo=Depends(get_repo)):
    try:
        return [
            IncidentEventOut.model_validate(event)
            for event in svc.list_events(repo, incident_id)
        ]
    except Exception as exc:
        _raise_api_error(exc)
