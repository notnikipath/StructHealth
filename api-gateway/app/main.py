from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.structhealth_common import (
    ProcessSensorBatchResult,
    Role,
    SensorBatchIngestRequest,
    Settings,
    sign_token,
    verify_token,
)


class GatewaySettings(BaseSettings):
    service_name: str = "api-gateway"
    service_port: int = 8500

    asset_service_url: str = "http://asset-service:8501"
    ingestion_service_url: str = "http://ingestion-service:8502"
    analysis_service_url: str = "http://analysis-service:8503"
    alert_service_url: str = "http://alert-service:8504"
    report_service_url: str = "http://report-service:8505"
    notification_service_url: str = "http://notification-service:8506"

    jwt_secret: str = Settings().jwt_secret
    token_exp_minutes: int = 240

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = GatewaySettings()
app = FastAPI(title="StructHealth API Gateway", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthRequest(BaseModel):
    user_id: str
    role: Role
    language: str = Field(default="ru", pattern="^(ru|en)$")


class DashboardQuery(BaseModel):
    asset_id: str
    actor_role: Role = Role.ENGINEER


AuthRequest.model_rebuild()
DashboardQuery.model_rebuild()


async def _post_json(client: httpx.AsyncClient, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = await client.post(url, json=payload)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


async def _put_json(client: httpx.AsyncClient, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = await client.put(url, json=payload)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


async def _get_json(client: httpx.AsyncClient, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = await client.get(url, params=params)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


def _service_urls() -> dict[str, str]:
    return {
        "asset": settings.asset_service_url,
        "ingestion": settings.ingestion_service_url,
        "analysis": settings.analysis_service_url,
        "alert": settings.alert_service_url,
        "report": settings.report_service_url,
        "notification": settings.notification_service_url,
    }


def _daily_metrics_from_readings(readings: list[dict[str, Any]]) -> dict[str, float]:
    max_vibration = 0.0
    max_tilt = 0.0
    max_crack = 0.0
    for item in readings:
        sensor_id = str(item.get("sensor_id", "")).upper()
        value = abs(float(item.get("value", 0)))
        if "ACC" in sensor_id:
            max_vibration = max(max_vibration, value)
        elif "INC" in sensor_id:
            max_tilt = max(max_tilt, value)
        elif "CRK" in sensor_id:
            max_crack = max(max_crack, value)
    return {"max_vibration": max_vibration, "max_tilt_deg": max_tilt, "max_crack_mm": max_crack}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/auth/token")
async def issue_token(request: AuthRequest) -> dict[str, str]:
    token = sign_token(
        {"sub": request.user_id, "role": request.role.value, "language": request.language},
        settings.jwt_secret,
        exp_minutes=settings.token_exp_minutes,
    )
    return {"access_token": token, "token_type": "Bearer"}


@app.post("/auth/verify")
async def verify_auth(token: str) -> dict[str, Any]:
    payload = verify_token(token, settings.jwt_secret)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


@app.get("/services/health")
async def service_health() -> dict[str, Any]:
    statuses: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, base_url in _service_urls().items():
            try:
                statuses[name] = await _get_json(client, f"{base_url}/health")
            except HTTPException as exc:
                statuses[name] = {"status": "error", "detail": exc.detail}
            except httpx.HTTPError as exc:
                statuses[name] = {"status": "error", "detail": str(exc)}
    return statuses


@app.post("/workflow/process-sensor-batch")
async def process_sensor_batch(request: SensorBatchIngestRequest) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        ingestion = await _post_json(
            client,
            f"{settings.ingestion_service_url}/ingestion/batch",
            request.model_dump(mode="json"),
        )
        analysis = await _post_json(
            client,
            f"{settings.analysis_service_url}/analysis/process-batch",
            {**request.model_dump(mode="json"), "actor_role": Role.ENGINEER.value},
        )
        alerts_created: list[dict[str, Any]] = []
        if analysis["anomalies"]:
            alert_payload = await _post_json(
                client,
                f"{settings.alert_service_url}/alerts/raise",
                {
                    "asset_id": request.asset_id,
                    "anomalies": analysis["anomalies"],
                    "residual_life_days": min(
                        (item["residual_life_days"] for item in analysis["summaries"]),
                        default=None,
                    ),
                    "actor_id": "gateway",
                    "actor_role": Role.ENGINEER.value,
                },
            )
            alerts_created = alert_payload["items"]
            critical_alerts = [item for item in alerts_created if item["severity"] == "critical"]
            for alert in critical_alerts:
                await _post_json(
                    client,
                    f"{settings.notification_service_url}/notify/critical",
                    {
                        "asset_id": request.asset_id,
                        "recipient": "oncall-engineer@structhealth.local",
                        "issue": alert["message"],
                        "actor_role": Role.ENGINEER.value,
                    },
                )
        daily_metrics = _daily_metrics_from_readings([item.model_dump(mode="json") for item in request.readings])
        report = await _post_json(
            client,
            f"{settings.report_service_url}/reports/daily/update",
            {
                "asset_id": request.asset_id,
                "readings_count": len(request.readings),
                "anomalies_count": len(analysis["anomalies"]),
                "max_vibration": daily_metrics["max_vibration"],
                "max_tilt_deg": daily_metrics["max_tilt_deg"],
                "max_crack_mm": daily_metrics["max_crack_mm"],
                "average_health_index": analysis["asset_health_index"],
                "actor_id": "gateway",
                "actor_role": Role.ENGINEER.value,
            },
        )
        await _post_json(
            client,
            f"{settings.report_service_url}/reports/metrics/latency",
            {"value_ms": analysis["processing_latency_ms"]},
        )
    result = ProcessSensorBatchResult(ingestion=ingestion, analysis=analysis, alerts=alerts_created, report=report)
    return result.model_dump(mode="json")


@app.get("/dashboard/{asset_id}")
async def dashboard(asset_id: str, actor_role: Role = Role.ENGINEER) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        asset = await _get_json(
            client,
            f"{settings.asset_service_url}/assets/{asset_id}",
            {"actor_role": actor_role.value},
        )
        sensors = await _get_json(
            client,
            f"{settings.asset_service_url}/assets/{asset_id}/sensors",
            {"actor_role": actor_role.value},
        )
        readings = await _get_json(
            client,
            f"{settings.ingestion_service_url}/ingestion/readings/{asset_id}",
            {"limit": 200, "actor_role": Role.OPERATOR.value},
        )
        ingestion_metrics = await _get_json(client, f"{settings.ingestion_service_url}/ingestion/metrics")
        anomalies = await _get_json(
            client,
            f"{settings.analysis_service_url}/analysis/anomalies/{asset_id}",
            {"limit": 100, "actor_role": actor_role.value},
        )
        trends = await _get_json(
            client,
            f"{settings.analysis_service_url}/analysis/trends/{asset_id}",
            {"days": 14, "actor_role": actor_role.value},
        )
        analysis_kpi = await _get_json(client, f"{settings.analysis_service_url}/analysis/kpi")
        alerts = await _get_json(
            client,
            f"{settings.alert_service_url}/alerts/{asset_id}",
            {"actor_role": actor_role.value},
        )
        notifications = await _get_json(
            client,
            f"{settings.notification_service_url}/notify/history",
            {"limit": 30, "actor_role": actor_role.value},
        )
        report_today = None
        try:
            report_today = await _get_json(
                client,
                f"{settings.report_service_url}/reports/daily/{asset_id}",
                {"actor_role": actor_role.value},
            )
        except HTTPException:
            report_today = {
                "asset_id": asset_id,
                "report_date": datetime.now(UTC).date().isoformat(),
                "readings_count": 0,
                "anomalies_count": 0,
                "average_health_index": 100,
            }
        report_trends = await _get_json(
            client,
            f"{settings.report_service_url}/reports/trends/{asset_id}",
            {"days": 14, "actor_role": actor_role.value},
        )
        quality_summary = await _get_json(client, f"{settings.report_service_url}/reports/summary")
    return {
        "asset": asset,
        "sensors": sensors,
        "readings": readings,
        "ingestion_metrics": ingestion_metrics,
        "anomalies": anomalies,
        "trends": trends,
        "analysis_kpi": analysis_kpi,
        "alerts": alerts,
        "notifications": notifications,
        "report_today": report_today,
        "report_trends": report_trends,
        "quality_summary": quality_summary,
    }


@app.put("/workflow/thresholds/{asset_id}/{sensor_id}")
async def set_threshold(asset_id: str, sensor_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    threshold = payload.get("threshold", {})
    actor_id = payload.get("actor_id", "gateway")
    actor_role = payload.get("actor_role", Role.ENGINEER.value)
    async with httpx.AsyncClient(timeout=15.0) as client:
        asset_side = await _put_json(
            client,
            f"{settings.asset_service_url}/assets/{asset_id}/sensors/{sensor_id}/thresholds",
            {
                "threshold": {
                    "warning": threshold["warning"],
                    "critical": threshold["critical"],
                    "direction": threshold.get("direction", "above"),
                    "unit": threshold["unit"],
                    "fatigue_limit": threshold.get("fatigue_limit"),
                },
                "actor_id": actor_id,
                "actor_role": actor_role,
            },
        )
        analysis_side = await _put_json(
            client,
            f"{settings.analysis_service_url}/analysis/thresholds",
            {
                "asset_id": asset_id,
                "sensor_id": sensor_id,
                "threshold": threshold,
                "actor_id": actor_id,
                "actor_role": actor_role,
            },
        )
    return {"asset_service": asset_side, "analysis_service": analysis_side}
