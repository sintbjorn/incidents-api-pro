from dataclasses import dataclass
from typing import Protocol

import httpx

from app.domain.models import Incident, NotificationChannel
from app.settings import settings


@dataclass(frozen=True, slots=True)
class NotificationResult:
    status: str
    notification_id: str | None = None
    error: str | None = None


class NotificationClient(Protocol):
    def send_incident_alert(
        self,
        incident: Incident,
        channel: NotificationChannel,
    ) -> NotificationResult: ...


class DisabledNotificationClient:
    def send_incident_alert(
        self,
        incident: Incident,
        channel: NotificationChannel,
    ) -> NotificationResult:
        return NotificationResult(status="SKIPPED", error="Notification service is disabled")


class HttpNotificationClient:
    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def send_incident_alert(
        self,
        incident: Incident,
        channel: NotificationChannel,
    ) -> NotificationResult:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/notifications/",
                    json={
                        "channel": channel.value,
                        "subject": f"[{incident.severity.value}] {incident.title}",
                        "message": incident.description,
                        "target": incident.target,
                        "metadata": {
                            "incident_id": incident.id,
                            "severity": incident.severity.value,
                            "source": incident.source.value,
                            "fingerprint": incident.fingerprint,
                        },
                    },
                    headers=headers,
                )
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPError as exc:
            return NotificationResult(status="FAILED", error=str(exc))

        notification_id = str(body.get("id") or body.get("notification_id") or "")
        return NotificationResult(status="SENT", notification_id=notification_id or None)


def get_notification_client() -> NotificationClient:
    if not settings.NOTIFICATION_SERVICE_URL:
        return DisabledNotificationClient()
    return HttpNotificationClient(
        settings.NOTIFICATION_SERVICE_URL,
        settings.NOTIFICATION_SERVICE_API_KEY,
        settings.NOTIFICATION_TIMEOUT_SECONDS,
    )
