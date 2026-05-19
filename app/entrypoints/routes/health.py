#хелсчек и метрики (прометеус сам отдает в правильно формате )
from fastapi import APIRouter
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from sqlalchemy import text

from app.adapters.db import SessionLocal

router = APIRouter()
REQS = Counter("requests_total", "Total HTTP requests")

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/health/live")
def live():
    return {"status": "alive"}

@router.get("/health/ready")
def ready():
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
    return {"status": "ready"}

@router.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
