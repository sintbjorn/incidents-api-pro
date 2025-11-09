#хелсчек и метрики (прометеус сам отдает в правильно формате )
from fastapi import APIRouter
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

router = APIRouter()
REQS = Counter("requests_total", "Total HTTP requests")

@router.get("/health")
def health():                       #минимально-просто ок здесь можно прикрутить проверку БД/кэша
    return {"status": "ok"}

@router.get("/metrics")
def metrics():                      #отдаем метрики в формате промет
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
