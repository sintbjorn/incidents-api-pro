#парсинг входа валид заголовки коды ошибок
from fastapi import APIRouter, Depends, HTTPException, Query, Response, Header
from app.schemas.incidents import IncidentOut, IncidentCreate, StatusUpdate  # ← одна схема на оба PATCH
from app.adapters.repo import SqlAlchemyIncidentsRepo
from app.adapters.db import session_dep
from app.domain.models import Status, Source
from app.services import incidents as svc

router = APIRouter()

def get_repo(s=Depends(session_dep)):
    # Отдаём репозиторий commit/rollback/close делает session_dep()
    return SqlAlchemyIncidentsRepo(s)

@router.post("/incidents", response_model=IncidentOut, status_code=201)
def create_incident(payload: IncidentCreate, repo=Depends(get_repo)):
    inc = svc.create(repo, payload.description, payload.source)
    return IncidentOut.model_validate(inc)

@router.get("/incidents", response_model=list[IncidentOut])
def list_incidents(
    response: Response,
    status: Status | None = Query(None),
    source: Source | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    repo=Depends(get_repo)
):
    items, total = svc.list_(repo, status, source, limit, offset)           #отдаю заголовки чтобы клиент мог удобно делать пагинацию
    response.headers["X-Total-Count"] = str(total)
    if items:
        response.headers["Content-Range"] = f"incidents {offset}-{offset+len(items)-1}/{total}"
    else:
        response.headers["Content-Range"] = f"incidents */{total}"
    return [IncidentOut.model_validate(i) for i in items]

@router.patch("/incidents/{incident_id}/status", response_model=IncidentOut)
def update_status(
    incident_id: int,
    payload: StatusUpdate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    repo=Depends(get_repo)
):
    #патчит только статус 
    try:
        inc = svc.update_status(repo, incident_id, payload.status, etag=if_match)
        out = IncidentOut.model_validate(inc)
        resp = Response(content=out.model_dump_json(), media_type="application/json")
        resp.headers["ETag"] = f"W/{out.id}-{out.status}"
        return resp
    except KeyError:
        raise HTTPException(404, "Incident not found")
    except ValueError as e:
        raise HTTPException(409, str(e))
    except PermissionError:
        raise HTTPException(412, "Precondition Failed (ETag mismatch)")

@router.patch("/incidents/{incident_id}", response_model=IncidentOut)
def update_incident(
    incident_id: int,
    payload: StatusUpdate,   # та же схема: можно и статус, и дописать описание
    if_match: str | None = Header(default=None, alias="If-Match"),
    repo=Depends(get_repo)
):
    try:
        inc = svc.update(repo, incident_id, payload.status, payload.description_append, etag=if_match)
        out = IncidentOut.model_validate(inc)
        resp = Response(content=out.model_dump_json(), media_type="application/json")
        resp.headers["ETag"] = f"W/{out.id}-{out.status}"
        return resp
    except KeyError:
        raise HTTPException(404, "Incident not found")
    except ValueError as e:
        raise HTTPException(409, str(e))
    except PermissionError:
        raise HTTPException(412, "Precondition Failed (ETag mismatch)")
