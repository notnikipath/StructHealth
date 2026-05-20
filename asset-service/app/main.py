from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.structhealth_common import (
    AssetCreateRequest,
    AssetPassport,
    AssetType,
    GeoPoint,
    Role,
    SensorNode,
    SensorRegistrationRequest,
    SensorThreshold,
    SensorType,
    Settings,
    build_audit_event,
    has_permission,
)

settings = Settings(service_name="asset-service", service_port=8501)
app = FastAPI(title="StructHealth Asset Service", version="1.0.0")


class ThresholdUpdateRequest(BaseModel):
    threshold: SensorThreshold
    actor_id: str
    actor_role: Role


def _seed_assets() -> dict[str, AssetPassport]:
    base = AssetPassport(
        asset_id="AST-BRIDGE-001",
        name="North River Bridge",
        asset_type=AssetType.BRIDGE,
        coordinates=GeoPoint(latitude=55.7522, longitude=37.6156, elevation_m=138),
        built_year=1998,
        materials=["steel", "reinforced_concrete"],
        design_life_years=120,
        owner="City Transport Authority",
    )
    base.sensors = [
        SensorNode(
            sensor_id="SNS-ACC-001",
            asset_id=base.asset_id,
            sensor_type=SensorType.ACCELEROMETER,
            placement="span-midpoint",
            axis="z",
            sampling_hz=100,
            threshold=SensorThreshold(warning=0.75, critical=1.1, unit="g", fatigue_limit=1.3),
        ),
        SensorNode(
            sensor_id="SNS-INC-001",
            asset_id=base.asset_id,
            sensor_type=SensorType.INCLINOMETER,
            placement="pier-2",
            axis="x",
            sampling_hz=20,
            threshold=SensorThreshold(warning=0.25, critical=0.45, unit="deg", fatigue_limit=0.5),
        ),
        SensorNode(
            sensor_id="SNS-CRK-001",
            asset_id=base.asset_id,
            sensor_type=SensorType.CRACK_METER,
            placement="expansion-joint-east",
            sampling_hz=5,
            threshold=SensorThreshold(warning=2.0, critical=3.2, unit="mm", fatigue_limit=3.5),
        ),
    ]
    return {base.asset_id: base}


assets: dict[str, AssetPassport] = _seed_assets()
audit_log: list[dict[str, Any]] = []


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


def _audit(actor_id: str, actor_role: Role, action: str, object_id: str, details: dict[str, Any] | None = None) -> None:
    audit_log.append(
        build_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            object_type="asset",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


def _find_sensor(asset: AssetPassport, sensor_id: str) -> SensorNode | None:
    for sensor in asset.sensors:
        if sensor.sensor_id == sensor_id:
            return sensor
    return None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/assets")
async def list_assets(asset_type: AssetType | None = None, actor_role: Role = Role.OPERATOR) -> dict[str, Any]:
    _assert_permission(actor_role, "asset:read")
    items = [
        item.model_dump(mode="json")
        for item in assets.values()
        if asset_type is None or item.asset_type == asset_type
    ]
    return {"items": items, "count": len(items)}


@app.get("/assets/{asset_id}")
async def get_asset(asset_id: str, actor_role: Role = Role.OPERATOR) -> dict[str, Any]:
    _assert_permission(actor_role, "asset:read")
    asset = assets.get(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset.model_dump(mode="json")


@app.post("/assets")
async def create_asset(request: AssetCreateRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "asset:create")
    asset = AssetPassport(
        asset_id=f"AST-{request.asset_type.value[:3].upper()}-{uuid4().hex[:8].upper()}",
        name=request.name,
        asset_type=request.asset_type,
        coordinates=request.coordinates,
        built_year=request.built_year,
        materials=request.materials,
        design_life_years=request.design_life_years,
        owner=request.owner,
    )
    assets[asset.asset_id] = asset
    _audit(request.actor_id, request.actor_role, "asset.create", asset.asset_id)
    return asset.model_dump(mode="json")


@app.get("/assets/{asset_id}/passport")
async def asset_passport(asset_id: str, actor_role: Role = Role.OPERATOR) -> dict[str, Any]:
    _assert_permission(actor_role, "asset:read")
    asset = assets.get(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    payload = asset.model_dump(mode="json")
    payload["generated_at"] = datetime.now(UTC).isoformat()
    return payload


@app.get("/assets/{asset_id}/sensors")
async def list_sensors(asset_id: str, actor_role: Role = Role.OPERATOR) -> dict[str, Any]:
    _assert_permission(actor_role, "asset:read")
    asset = assets.get(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"asset_id": asset_id, "items": [sensor.model_dump(mode="json") for sensor in asset.sensors]}


@app.post("/assets/{asset_id}/sensors")
async def register_sensor(asset_id: str, request: SensorRegistrationRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "asset:update")
    asset = assets.get(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    sensor = SensorNode(
        sensor_id=f"SNS-{request.sensor_type.value[:3].upper()}-{uuid4().hex[:8].upper()}",
        asset_id=asset_id,
        sensor_type=request.sensor_type,
        placement=request.placement,
        axis=request.axis,
        sampling_hz=request.sampling_hz,
        calibration_offset=request.calibration_offset,
        threshold=request.threshold,
    )
    asset.sensors.append(sensor)
    _audit(request.actor_id, request.actor_role, "asset.sensor.register", sensor.sensor_id, {"asset_id": asset_id})
    return sensor.model_dump(mode="json")


@app.put("/assets/{asset_id}/sensors/{sensor_id}/thresholds")
async def update_sensor_threshold(
    asset_id: str,
    sensor_id: str,
    request: ThresholdUpdateRequest,
) -> dict[str, Any]:
    _assert_permission(request.actor_role, "asset:update")
    asset = assets.get(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    sensor = _find_sensor(asset, sensor_id)
    if sensor is None:
        raise HTTPException(status_code=404, detail="Sensor not found")
    sensor.threshold = request.threshold
    _audit(request.actor_id, request.actor_role, "asset.sensor.threshold.update", sensor_id, {"asset_id": asset_id})
    return sensor.model_dump(mode="json")


@app.get("/assets/{asset_id}/sensor-layout")
async def sensor_layout(asset_id: str, actor_role: Role = Role.OPERATOR) -> dict[str, Any]:
    _assert_permission(actor_role, "asset:read")
    asset = assets.get(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    layout = [
        {
            "sensor_id": sensor.sensor_id,
            "sensor_type": sensor.sensor_type,
            "placement": sensor.placement,
            "axis": sensor.axis,
            "sampling_hz": sensor.sampling_hz,
        }
        for sensor in asset.sensors
    ]
    return {"asset_id": asset_id, "asset_name": asset.name, "layout": layout}


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}
