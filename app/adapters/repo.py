#обертка над орм, тут будет вся работа с базой в одном месте
# покрытие сервисов тестами через фейк репу
from typing import Protocol
from sqlalchemy.orm import Session
from app.adapters.orm import IncidentORM
from app.domain.models import Incident, Status, Source

class IncidentsRepo(Protocol):
    def add(self, i: Incident) -> Incident: ...
    def get(self, id_: int) -> Incident | None: ...
    def list(self, status: Status | None, source: Source | None, limit: int, offset: int) -> tuple[list[Incident], int]: ...
    def update_status(self, id_: int, new: Status, etag: str | None = None) -> Incident: ...
    def update(self, id_: int, new_status: Status | None, description_append: str | None, etag: str | None = None) -> Incident: ...

class SqlAlchemyIncidentsRepo:
    def __init__(self, session: Session):
        self.s = session
    def update(self, id_: int, new_status: Status | None, description_append: str | None, etag: str | None = None) -> Incident:
        row = self.s.get(IncidentORM, id_)
        if not row:
            raise KeyError("not found")
        if etag and etag != row.etag():
            raise PermissionError("etag mismatch")
        #меняем если он рил пришел
        if new_status is not None:
            row.status = new_status
        #описание допис в конец а не заменяем
        if description_append:
            row.description = (row.description.rstrip() + "\n" + description_append.strip()).strip()

        self.s.add(row)
        self.s.flush()
        self.s.refresh(row)
        return row.to_domain()

    def add(self, i: Incident) -> Incident:
        #иницилизацию статуса делаю в доменной фабрике, а тут прост сохраняю
        row = IncidentORM(description=i.description, status=i.status, source=i.source)
        self.s.add(row)
        self.s.flush() #нуден id
        self.s.refresh(row)
        return row.to_domain()

    def get(self, id_: int) -> Incident | None:
        row = self.s.get(IncidentORM, id_)
        return row.to_domain() if row else None

    def list(self, status, source, limit, offset):
        #фильтр по статусу и источнику (сорт по времени созд и id)
        q = self.s.query(IncidentORM)
        if status:
            q = q.filter(IncidentORM.status == status)
        if source:
            q = q.filter(IncidentORM.source == source)
        total = q.count()
        items = (q.order_by(IncidentORM.created_at.desc(), IncidentORM.id.desc())
                   .offset(offset).limit(limit).all())
        return [r.to_domain() for r in items], total

    def update_status(self, id_: int, new: Status, etag: str | None = None) -> Incident:
        row = self.s.get(IncidentORM, id_)
        if not row:
            raise KeyError("not found")
        #если прислали if-match-сверяем а если не совпало-412
        if etag and etag != row.etag():
            raise PermissionError("etag mismatch")
        row.status = new
        self.s.add(row)
        self.s.flush()
        self.s.refresh(row)
        return row.to_domain()
