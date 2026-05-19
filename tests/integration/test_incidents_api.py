from app.adapters.notifications import NotificationResult
from app.domain.models import NotificationChannel
from app.entrypoints.api import app
from app.entrypoints.routes.incidents import get_notification_client


class FakeNotificationClient:
    def send_incident_alert(self, incident, channel: NotificationChannel) -> NotificationResult:
        return NotificationResult(status="SENT", notification_id=f"notif-{incident.id}")


def incident_payload(**overrides):
    payload = {
        "title": "High API latency",
        "description": "P95 latency is above 1500ms",
        "severity": "WARNING",
        "source": "monitoring",
        "fingerprint": "renovation-flip-api:latency:p95",
        "target": "renovation-flip-api",
    }
    payload.update(overrides)
    return payload


def test_incident_lifecycle_events_and_etag(client):
    r = client.post("/api/v1/incidents", json=incident_payload())
    assert r.status_code == 201, r.text
    inc = r.json()
    assert inc["status"] == "NEW"
    assert inc["version"] == 1
    iid = inc["id"]
    assert r.headers["etag"] == f'W/"incident-{iid}-v1"'

    r = client.post(f"/api/v1/incidents/{iid}/ack")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ACKNOWLEDGED"
    assert r.json()["version"] == 2

    stale = client.patch(
        f"/api/v1/incidents/{iid}",
        headers={"If-Match": f'W/"incident-{iid}-v1"'},
        json={"status": "IN_PROGRESS"},
    )
    assert stale.status_code == 412

    r = client.patch(
        f"/api/v1/incidents/{iid}",
        headers={"If-Match": f'W/"incident-{iid}-v2"'},
        json={"status": "IN_PROGRESS"},
    )
    assert r.status_code == 200, r.text
    assert r.headers["etag"] == f'W/"incident-{iid}-v3"'

    r = client.post(f"/api/v1/incidents/{iid}/resolve", json={"comment": "fixed after restart"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "RESOLVED"
    assert r.json()["resolved_at"] is not None

    r = client.post(f"/api/v1/incidents/{iid}/close")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "CLOSED"
    assert r.json()["closed_at"] is not None

    r = client.get(f"/api/v1/incidents/{iid}/events")
    assert r.status_code == 200
    event_types = [event["event_type"] for event in r.json()]
    assert event_types == [
        "CREATED",
        "STATUS_CHANGED",
        "STATUS_CHANGED",
        "STATUS_CHANGED",
        "COMMENT_ADDED",
        "STATUS_CHANGED",
    ]


def test_signal_deduplicates_open_incident(client):
    r = client.post("/api/v1/signals", json=incident_payload(fingerprint="api:5xx"))
    assert r.status_code == 201, r.text
    first = r.json()

    r = client.post(
        "/api/v1/signals",
        json=incident_payload(description="5xx is still high", fingerprint="api:5xx"),
    )
    assert r.status_code == 202, r.text
    second = r.json()
    assert second["id"] == first["id"]
    assert second["occurrence_count"] == 2
    assert second["version"] == 2

    r = client.get(f"/api/v1/incidents/{first['id']}/events")
    assert [event["event_type"] for event in r.json()] == ["CREATED", "SIGNAL_RECEIVED"]


def test_signal_reopens_resolved_incident(client):
    r = client.post("/api/v1/signals", json=incident_payload(fingerprint="api:reopen"))
    iid = r.json()["id"]
    assert client.post(f"/api/v1/incidents/{iid}/ack").status_code == 200
    assert client.patch(f"/api/v1/incidents/{iid}", json={"status": "IN_PROGRESS"}).status_code == 200
    assert client.post(f"/api/v1/incidents/{iid}/resolve").status_code == 200

    r = client.post(
        "/api/v1/signals",
        json=incident_payload(fingerprint="api:reopen", description="latency is back"),
    )
    assert r.status_code == 202, r.text
    reopened = r.json()
    assert reopened["id"] == iid
    assert reopened["status"] == "IN_PROGRESS"
    assert reopened["resolved_at"] is None
    assert reopened["occurrence_count"] == 2

    r = client.get(f"/api/v1/incidents/{iid}/events")
    payloads = [event["payload"] for event in r.json() if event["event_type"] == "STATUS_CHANGED"]
    assert {"from_status": "RESOLVED", "to_status": "IN_PROGRESS", "reason": "signal_reappeared"} in payloads


def test_critical_incident_requests_notification(client):
    app.dependency_overrides[get_notification_client] = lambda: FakeNotificationClient()
    try:
        r = client.post(
            "/api/v1/signals",
            json=incident_payload(severity="CRITICAL", fingerprint="api:critical"),
        )
        assert r.status_code == 201, r.text
        iid = r.json()["id"]

        r = client.get(f"/api/v1/incidents/{iid}/notifications")
        assert r.status_code == 200, r.text
        notifications = r.json()
        assert notifications[0]["status"] == "SENT"
        assert notifications[0]["channel"] == "telegram"
        assert notifications[0]["notification_id"] == f"notif-{iid}"

        r = client.get(f"/api/v1/incidents/{iid}/events")
        assert "NOTIFICATION_SENT" in [event["event_type"] for event in r.json()]
    finally:
        app.dependency_overrides.clear()


def test_invalid_transition_is_conflict(client):
    r = client.post("/api/v1/incidents", json=incident_payload(fingerprint="api:db"))
    iid = r.json()["id"]

    r = client.patch(f"/api/v1/incidents/{iid}/status", json={"status": "RESOLVED"})
    assert r.status_code == 409

    r = client.patch("/api/v1/incidents/999999/status", json={"status": "IN_PROGRESS"})
    assert r.status_code == 404


def test_resolve_accepts_empty_body(client):
    r = client.post("/api/v1/incidents", json=incident_payload(fingerprint="api:empty-resolve"))
    iid = r.json()["id"]
    assert client.post(f"/api/v1/incidents/{iid}/ack").status_code == 200
    r = client.patch(f"/api/v1/incidents/{iid}/status", json={"status": "IN_PROGRESS"})
    assert r.status_code == 200

    r = client.post(f"/api/v1/incidents/{iid}/resolve")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "RESOLVED"
