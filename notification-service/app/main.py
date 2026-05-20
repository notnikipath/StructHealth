from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.structhealth_common import NotificationPayload, Role, Settings, Severity, has_permission

settings = Settings(service_name="notification-service", service_port=8506)
app = FastAPI(title="StructHealth Notification Service", version="1.0.0")

messages: list[dict[str, Any]] = []


class CriticalNotificationRequest(BaseModel):
    asset_id: str
    recipient: str
    issue: str
    actor_role: Role


CriticalNotificationRequest.model_rebuild()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/notify/send")
async def send_notification(payload: NotificationPayload) -> dict[str, Any]:
    _assert_permission(payload.actor_role, "notification:send")
    item = payload.model_dump(mode="json")
    item["status"] = "queued"
    item["sent_at"] = datetime.now(UTC).isoformat()
    messages.append(item)
    return item


@app.post("/notify/critical")
async def notify_critical(request: CriticalNotificationRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "notification:send")
    item = {
        "channel": "sms",
        "recipient": request.recipient,
        "subject": f"Critical alert for {request.asset_id}",
        "body": request.issue,
        "severity": Severity.CRITICAL.value,
        "status": "queued",
        "sent_at": datetime.now(UTC).isoformat(),
    }
    messages.append(item)
    return item


@app.get("/notify/history")
async def history(limit: int = 100, actor_role: Role = Role.ENGINEER) -> dict[str, Any]:
    _assert_permission(actor_role, "notification:read")
    return {"items": messages[-limit:], "count": min(limit, len(messages))}
