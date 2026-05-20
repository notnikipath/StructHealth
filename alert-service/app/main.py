from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.structhealth_common import (
    AlertCreateRequest,
    AlertRecord,
    Role,
    Settings,
    Severity,
    has_permission,
)

settings = Settings(service_name="alert-service", service_port=8504)
app = FastAPI(title="StructHealth Alert Service", version="1.0.0")


class FatigueForecastRequest(BaseModel):
    asset_id: str
    damage_samples: list[float] = Field(default_factory=list)
    actor_id: str
    actor_role: Role


class AlertAcknowledgeRequest(BaseModel):
    actor_id: str
    actor_role: Role
    comment: str | None = None


FatigueForecastRequest.model_rebuild()
AlertAcknowledgeRequest.model_rebuild()

alerts_by_asset: dict[str, list[AlertRecord]] = defaultdict(list)


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/alerts/raise")
async def raise_alert(request: AlertCreateRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "alert:create")
    if not request.anomalies and request.residual_life_days is None:
        return {"asset_id": request.asset_id, "created": 0, "items": []}
    severity = Severity.WARNING
    if any(item.severity == Severity.CRITICAL for item in request.anomalies):
        severity = Severity.CRITICAL
    if request.residual_life_days is not None and request.residual_life_days < 30:
        severity = Severity.CRITICAL
    title = "Structural risk event detected"
    if severity == Severity.CRITICAL:
        title = "CRITICAL structural risk detected"
    message = (
        f"Detected {len(request.anomalies)} anomalies"
        f"{'' if request.residual_life_days is None else f', residual life ~ {request.residual_life_days:.1f} days'}."
    )
    alert = AlertRecord(
        alert_id=f"ALT-{uuid4().hex[:10].upper()}",
        asset_id=request.asset_id,
        severity=severity,
        title=title,
        message=message,
        anomaly_ids=[item.event_id for item in request.anomalies],
        predicted_failure_days=request.residual_life_days,
    )
    alerts_by_asset[request.asset_id].append(alert)
    return {"asset_id": request.asset_id, "created": 1, "items": [alert.model_dump(mode="json")]}


@app.post("/alerts/fatigue-forecast")
async def fatigue_forecast(request: FatigueForecastRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "alert:create")
    if not request.damage_samples:
        return {"asset_id": request.asset_id, "risk_level": "low", "score": 0.0}
    score = round(min(1.0, mean(request.damage_samples[-20:]) * 1.35), 3)
    risk = "low"
    if score > 0.45:
        risk = "medium"
    if score > 0.75:
        risk = "high"
    return {"asset_id": request.asset_id, "risk_level": risk, "score": score}


@app.get("/alerts/{asset_id}")
async def list_alerts(asset_id: str, status: str | None = None, actor_role: Role = Role.ENGINEER) -> dict[str, Any]:
    _assert_permission(actor_role, "alert:read")
    items = []
    for alert in alerts_by_asset.get(asset_id, []):
        if status and alert.status != status:
            continue
        items.append(alert.model_dump(mode="json"))
    return {"asset_id": asset_id, "items": items, "count": len(items)}


@app.post("/alerts/{asset_id}/{alert_id}/ack")
async def ack_alert(asset_id: str, alert_id: str, request: AlertAcknowledgeRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "alert:read")
    for alert in alerts_by_asset.get(asset_id, []):
        if alert.alert_id == alert_id:
            alert.status = "acknowledged"
            if request.comment:
                alert.message = f"{alert.message} Ack: {request.comment}"
            return alert.model_dump(mode="json")
    raise HTTPException(status_code=404, detail="Alert not found")
