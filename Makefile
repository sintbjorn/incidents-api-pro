.PHONY: dev run lint fmt test migrate seed alembic_init
dev: fmt lint migrate run
run:
	uvicorn app.entrypoints.api:app --reload --host 0.0.0.0 --port 8000
lint:
	ruff check . || true
fmt:
	black . && isort .
test:
	pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing
migrate:
	alembic upgrade head
alembic_init:
	alembic revision --autogenerate -m "init"
seed:
	python -c "from app.adapters.db import SessionLocal; from app.adapters.repo import SqlAlchemyIncidentsRepo; from app.domain.models import Source; from app.services.incidents import create; s=SessionLocal(); r=SqlAlchemyIncidentsRepo(s); [create(r, f'demo #'+str(i), Source.monitoring) for i in range(1,6)]; s.commit(); s.close()"
