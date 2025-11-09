#сервис слой - тут бизнес правила 
from app.domain.models import Incident, Status, Source
from app.domain.rules import ensure_transition
from app.adapters.repo import IncidentsRepo

def create(repo: IncidentsRepo, description: str, source: Source) -> Incident:          #конструируем доменную сущность и отдаем в репу
    return repo.add(Incident.new(description=description, source=source))

def list_(repo: IncidentsRepo, status: Status | None, source: Source | None, limit: int, offset: int):
    return repo.list(status, source, limit, offset)

def update_status(repo: IncidentsRepo, id_: int, new: Status, etag: str | None = None) -> Incident:
    current = repo.get(id_)
    if not current:
        raise KeyError("not found")     #пробрасываю через фсм недопустимые переходы отстреливаются 409 в веб-слое
    ensure_transition(current.status, new)
    return repo.update_status(id_, new, etag)

def update(repo: IncidentsRepo, id_: int, new_status: Status | None, description_append: str | None, etag: str | None = None) -> Incident:
    current = repo.get(id_)
    if not current:
        raise KeyError("not found")
    # валидируем только если статус действительно меняем
    if new_status is not None:
        ensure_transition(current.status, new_status)
    return repo.update(id_, new_status, description_append, etag)