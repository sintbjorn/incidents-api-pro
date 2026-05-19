# PulseWatch Incident Service

Detect, deduplicate, track, and notify production incidents.

PulseWatch is a production-ready incident management microservice. It accepts operational signals from monitoring, operators, partners, and systems; creates or deduplicates incidents by fingerprint; tracks lifecycle state; keeps an audit trail; exposes Prometheus metrics; and is ready to integrate with a dedicated Notification Service.

## Core Model

`Incident`

- `id: int`
- `title: str`
- `description: str`
- `status: NEW | ACKNOWLEDGED | IN_PROGRESS | RESOLVED | CLOSED`
- `severity: INFO | WARNING | CRITICAL`
- `source: operator | monitoring | partner | system`
- `fingerprint: str`
- `target: str`
- `created_at`, `updated_at`, `resolved_at`, `closed_at`
- `last_seen_at`, `occurrence_count`
- `version: int`

`IncidentEvent`

- `id`
- `incident_id`
- `event_type: CREATED | SIGNAL_RECEIVED | STATUS_CHANGED | COMMENT_ADDED | NOTIFICATION_SENT | AUTO_RESOLVED`
- `payload: JSON`
- `created_at`

Lifecycle:

```text
NEW -> ACKNOWLEDGED -> IN_PROGRESS <-> RESOLVED -> CLOSED
```

`fingerprint` is the deduplication key, usually built from `target + source + error_code/title`. Repeated open signals update `last_seen_at`, increment `occurrence_count`, bump `version`, and append an audit event instead of creating duplicate incidents.

## Quick Start

```bash
cp .env.example .env
docker-compose up --build
```

API: `http://localhost:8000`
Swagger: `http://localhost:8000/docs`
Health: `http://localhost:8000/health/live`, `http://localhost:8000/health/ready`
Metrics: `http://localhost:8000/metrics`

Local:

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.entrypoints.api:app --reload
```

## Endpoints

- `POST /api/v1/signals` - ingest monitoring/operator/partner signal with fingerprint deduplication
- `POST /api/v1/incidents` - create incident directly
- `GET /api/v1/incidents?status=NEW&source=monitoring&limit=50&offset=0` - list incidents
- `GET /api/v1/incidents/{id}` - incident details
- `PATCH /api/v1/incidents/{id}` - update status and/or append description
- `POST /api/v1/incidents/{id}/ack` - acknowledge incident
- `POST /api/v1/incidents/{id}/resolve` - resolve incident, optionally with comment
- `POST /api/v1/incidents/{id}/close` - close incident
- `POST /api/v1/incidents/{id}/comments` - append operator comment
- `GET /api/v1/incidents/{id}/events` - audit trail
- `GET /health/live` - liveness
- `GET /health/ready` - DB readiness
- `GET /metrics` - Prometheus metrics

List responses include `X-Total-Count` and `Content-Range`.

## Signal Example

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/signals \
  -H "Content-Type: application/json" \
  -d '{
    "source": "monitoring",
    "target": "renovation-flip-api",
    "title": "High API latency",
    "description": "P95 latency is above 1500ms",
    "severity": "WARNING",
    "fingerprint": "renovation-flip-api:latency:p95"
  }'
```

First signal returns `201 Created`. Repeated open signals with the same fingerprint return `202 Accepted` and update the existing incident.

## Optimistic Locking

ETags are based on the incident version:

```text
ETag: W/"incident-1-v3"
If-Match: W/"incident-1-v3"
```

Every material change increments `version`. A stale `If-Match` returns `412 Precondition Failed`.

## Prometheus Metrics

- `incidents_created_total{severity,source}`
- `incident_signals_deduplicated_total{severity,source}`
- `incident_status_transitions_total{from_status,to_status}`
- `requests_total`

## Notification Service Integration

PulseWatch is designed to call a separate Notification Service when a critical incident is created:

```text
PulseWatch Incident Service
  -> POST /api/notifications/
  -> Notification Service
  -> Email / Telegram / SMS
```

The current domain already includes `NOTIFICATION_SENT` events, so delivery requests can be audited without mixing incident lifecycle with notification transport.

## Renovation Flip Examples

- `renovation-flip-api down`
- `property ingestion job failed`
- `high 5xx error rate`
- `listing parser stopped receiving data`
- `payment webhook latency high`
- `notification delivery failures increased`
- `database readiness failed`

## Quality Gates

```bash
pytest -q
ruff check .
mypy app
alembic upgrade head
docker build .
```
