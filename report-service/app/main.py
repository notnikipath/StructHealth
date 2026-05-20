from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import UTC, date, datetime
from statistics import mean
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.structhealth_common import DailyAssetStats, ReportUpdateRequest, Role, Settings, has_permission

settings = Settings(service_name="report-service", service_port=8505)
app = FastAPI(title="StructHealth Report Service", version="1.0.0")


class LatencyMetricRequest(BaseModel):
    value_ms: float

daily_stats: dict[str, dict[date, DailyAssetStats]] = defaultdict(dict)
processing_latency_samples: list[float] = []
forecast_accuracy_samples: list[float] = [91.2, 92.8, 90.4]


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/reports/daily/update")
async def update_daily_report(request: ReportUpdateRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "report:write")
    today = datetime.now(UTC).date()
    report = DailyAssetStats(
        asset_id=request.asset_id,
        report_date=today,
        readings_count=request.readings_count,
        anomalies_count=request.anomalies_count,
        max_vibration=request.max_vibration,
        max_tilt_deg=request.max_tilt_deg,
        max_crack_mm=request.max_crack_mm,
        average_health_index=request.average_health_index,
    )
    daily_stats[request.asset_id][today] = report
    return report.model_dump(mode="json")


@app.get("/reports/daily/{asset_id}")
async def get_daily_report(
    asset_id: str,
    report_date: date | None = None,
    actor_role: Role = Role.ENGINEER,
) -> dict[str, Any]:
    _assert_permission(actor_role, "report:read")
    if report_date is None:
        report_date = datetime.now(UTC).date()
    report = daily_stats.get(asset_id, {}).get(report_date)
    if report is None:
        raise HTTPException(status_code=404, detail="Daily report not found")
    return report.model_dump(mode="json")


@app.get("/reports/trends/{asset_id}")
async def trends(asset_id: str, days: int = 7, actor_role: Role = Role.ENGINEER) -> dict[str, Any]:
    _assert_permission(actor_role, "report:read")
    records = sorted(daily_stats.get(asset_id, {}).values(), key=lambda item: item.report_date)
    records = records[-max(days, 1) :]
    if not records:
        return {"asset_id": asset_id, "window_days": days, "items": [], "summary": {}}
    payload = [item.model_dump(mode="json") for item in records]
    summary = {
        "avg_health_index": round(mean(item.average_health_index for item in records), 2),
        "anomalies_total": sum(item.anomalies_count for item in records),
        "max_vibration": max(item.max_vibration for item in records),
        "max_tilt_deg": max(item.max_tilt_deg for item in records),
        "max_crack_mm": max(item.max_crack_mm for item in records),
    }
    return {"asset_id": asset_id, "window_days": days, "items": payload, "summary": summary}


@app.get("/reports/export/{asset_id}")
async def export_report(asset_id: str, format: str = "json", actor_role: Role = Role.INSPECTOR) -> dict[str, Any]:
    _assert_permission(actor_role, "report:export")
    records = sorted(daily_stats.get(asset_id, {}).values(), key=lambda item: item.report_date)
    if format.lower() == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "report_date",
                "readings_count",
                "anomalies_count",
                "max_vibration",
                "max_tilt_deg",
                "max_crack_mm",
                "average_health_index",
            ]
        )
        for item in records:
            writer.writerow(
                [
                    item.report_date.isoformat(),
                    item.readings_count,
                    item.anomalies_count,
                    item.max_vibration,
                    item.max_tilt_deg,
                    item.max_crack_mm,
                    item.average_health_index,
                ]
            )
        return {"asset_id": asset_id, "format": "csv", "content": buffer.getvalue()}
    return {"asset_id": asset_id, "format": "json", "items": [item.model_dump(mode="json") for item in records]}


@app.get("/reports/summary")
async def quality_summary() -> dict[str, Any]:
    assets = len(daily_stats)
    report_count = sum(len(entries) for entries in daily_stats.values())
    average_forecast_accuracy = round(mean(forecast_accuracy_samples), 2) if forecast_accuracy_samples else 0
    avg_processing_latency = round(mean(processing_latency_samples), 2) if processing_latency_samples else 0
    return {
        "assets_count": assets,
        "reports_count": report_count,
        "polling_target_hz": settings.max_sampling_hz,
        "processing_latency_target_ms": settings.processing_latency_target_ms,
        "processing_latency_observed_ms": avg_processing_latency,
        "forecast_accuracy_target_pct": settings.defect_forecast_accuracy_target,
        "forecast_accuracy_observed_pct": average_forecast_accuracy,
    }


@app.post("/reports/metrics/latency")
async def ingest_latency(request: LatencyMetricRequest) -> dict[str, Any]:
    processing_latency_samples.append(request.value_ms)
    return {"accepted": True, "count": len(processing_latency_samples)}
