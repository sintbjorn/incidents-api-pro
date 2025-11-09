# ORM слой: описываем таблицы так, чтобы их можно было легко привести к доменным моделям

from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Enum, DateTime, func, Integer
from app.domain.models import Status, Source, Incident
from datetime import datetime

Base = declarative_base()

class IncidentORM(Base):
    __tablename__ = "incidents"
    # типизируем поля, mapped из sqlalchemy
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    #енум сохраняю как енум в бд (прост удобнее мигрировать и валидировать)
    status: Mapped[Status] = mapped_column(Enum(Status), nullable=False, default=Status.NEW)
    source: Mapped[Source] = mapped_column(Enum(Source), nullable=False)
    # created_at выставляет бд (server_default=now) корректно при множестве инстансов API
    created_at: Mapped[datetime] = mapped_column(  # ← datetime (не DateTime)
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def to_domain(self) -> Incident:
        #простое преобразование ORM -> доменная сущность (dataclass)
        return Incident(self.id, self.description, self.status, self.source, self.created_at)

    def etag(self) -> str:
        #етаг для оптимистической блокировки
        return f"W/{self.id}-{self.status}"
