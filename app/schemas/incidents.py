#pydantic схемы 
from pydantic import BaseModel, Field
from datetime import datetime
from app.domain.models import Status, Source

class IncidentCreate(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    source: Source
    status: Status | None = None  #status можно было бы передавать, но по бизнес-логике стартуем всегда с new-созадаю в домене

class IncidentOut(BaseModel):
    id: int
    description: str
    status: Status
    source: Source
    created_at: datetime

    class Config:
        from_attributes = True #умеем строиться из орм/датакласса

class StatusUpdate(BaseModel):
    #оставляю одну схему для двух патчей (смену статуса) (добавл описания)
    status: Status | None = None
    description_append: str | None = None

