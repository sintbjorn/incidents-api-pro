# модельки без привязки к бд или вебу можно мокать валидировать и тестить 
from enum import StrEnum
from dataclasses import dataclass
from datetime import datetime, timezone

class Status(StrEnum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class Source(StrEnum):
    operator = "operator"
    monitoring = "monitoring"
    partner = "partner"

@dataclass(frozen=True, slots=True)
class Incident:
    id: int | None
    description: str
    status: Status
    source: Source
    created_at: datetime

    @staticmethod
    def new(description: str, source: Source) -> "Incident":
        #фабрика нового инца, статус новый ставлю чтобы источник истинных данных был в доменен а не в вебе или орм
        return Incident(
            id=None,
            description=description,
            status=Status.NEW,
            source=source,
            created_at=datetime.now(timezone.utc),
        )
