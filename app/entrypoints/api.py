# app/entrypoints/api.py

from fastapi import FastAPI
from sqlalchemy.exc import OperationalError
import time

from app.entrypoints.routes import incidents, health
from app.adapters.orm import Base
from app.adapters.db import engine

app = FastAPI(title="Incidents API", version="1.0.0")

# dev: ждём БД и создаем таблицы
for _ in range(30):
    try:
        Base.metadata.create_all(bind=engine)
        break
    except OperationalError:
        time.sleep(1)

# БЕЗ prefix="/"
app.include_router(health.router)

app.include_router(incidents.router, prefix="/api/v1", tags=["incidents"])
