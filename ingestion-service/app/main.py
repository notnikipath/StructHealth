from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.structhealth_common import (
    Role,
    SensorBatchIngestRequest,
    SensorReading,
    Settings,
    asset_shard,
    estimate_polling_hz,
    has_permission,
    stream_processing_plan,
)

settings = Settings(service_name="ingestion-service", service_port=8502)


class SensorConnectionRequest(BaseModel):
    sensor_id: str
    asset_id: str
    protocol: str = Field(default="mqtt", pattern="^(mqtt|http|kafka)$")
    sampling_hz: float = Field(gt=0, le=100)
    actor_id: str
    actor_role: Role


SensorConnectionRequest.model_rebuild()

connected_sensors: dict[str, dict[str, Any]] = {}
readings_by_asset: dict[str, list[SensorReading]] = defaultdict(list)
readings_by_shard: dict[int, list[SensorReading]] = defaultdict(list)
write_queue: asyncio.Queue[SensorReading] = asyncio.Queue()
persisted_counter = 0
ingestion_latencies_ms: list[float] = []
_queue_worker_task: asyncio.Task[None] | None = None


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


async def _queue_writer() -> None:
    global persisted_counter
    while True:
        reading = await write_queue.get()
        try:
            await asyncio.sleep(0)
            persisted_counter += 1
            shard = asset_shard(reading.asset_id, settings.ingestion_stream_shards)
            readings_by_shard[shard].append(reading)
        finally:
            write_queue.task_done()


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _queue_worker_task
    if _queue_worker_task is None:
        _queue_worker_task = asyncio.create_task(_queue_writer())
    try:
        yield
    finally:
        if _queue_worker_task is not None:
            _queue_worker_task.cancel()
            with suppress(asyncio.CancelledError):
                await _queue_worker_task
            _queue_worker_task = None


app = FastAPI(title="StructHealth Ingestion Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/sensors/connect")
async def connect_sensor(request: SensorConnectionRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "ingestion:write")
    connected_sensors[request.sensor_id] = {
        "sensor_id": request.sensor_id,
        "asset_id": request.asset_id,
        "protocol": request.protocol,
        "sampling_hz": request.sampling_hz,
        "connected_at": datetime.now(UTC).isoformat(),
    }
    return connected_sensors[request.sensor_id]


@app.get("/sensors/connections")
async def sensor_connections(asset_id: str | None = None) -> dict[str, Any]:
    items = []
    for entry in connected_sensors.values():
        if asset_id and entry["asset_id"] != asset_id:
            continue
        items.append(entry)
    return {"items": items, "count": len(items)}


@app.post("/ingestion/batch")
async def ingest_batch(request: SensorBatchIngestRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "ingestion:write")
    if not request.readings:
        return {"asset_id": request.asset_id, "accepted": 0, "queue_depth": write_queue.qsize(), "shard_id": 0}
    started = time.perf_counter()
    for reading in request.readings:
        if reading.asset_id != request.asset_id:
            raise HTTPException(status_code=400, detail="Asset id mismatch in reading payload")
        if reading.sampling_hz > settings.max_sampling_hz:
            raise HTTPException(
                status_code=422,
                detail=f"Sampling frequency {reading.sampling_hz} exceeds {settings.max_sampling_hz} Hz",
            )
        readings_by_asset[request.asset_id].append(reading)
        await write_queue.put(reading)
    latency_ms = (time.perf_counter() - started) * 1000
    ingestion_latencies_ms.append(latency_ms)
    shard = asset_shard(request.asset_id, settings.ingestion_stream_shards)
    return {
        "asset_id": request.asset_id,
        "accepted": len(request.readings),
        "queue_depth": write_queue.qsize(),
        "shard_id": shard,
        "latency_ms": round(latency_ms, 3),
        "source": request.source,
    }


@app.get("/ingestion/readings/{asset_id}")
async def get_readings(asset_id: str, limit: int = 500, actor_role: Role = Role.OPERATOR) -> dict[str, Any]:
    _assert_permission(actor_role, "ingestion:read")
    items = [item.model_dump(mode="json") for item in readings_by_asset.get(asset_id, [])[-limit:]]
    return {"asset_id": asset_id, "items": items, "count": len(items)}


@app.get("/ingestion/metrics")
async def ingestion_metrics() -> dict[str, Any]:
    timestamps = []
    for asset_items in readings_by_asset.values():
        timestamps.extend(reading.timestamp for reading in asset_items[-200:])
    average_polling_hz = estimate_polling_hz(timestamps)
    avg_latency_ms = (
        round(sum(ingestion_latencies_ms) / len(ingestion_latencies_ms), 3) if ingestion_latencies_ms else 0
    )
    return {
        "connected_sensors": len(connected_sensors),
        "queue_depth": write_queue.qsize(),
        "persisted_count": persisted_counter,
        "assets_tracked": len(readings_by_asset),
        "avg_polling_hz": average_polling_hz,
        "max_polling_hz_target": settings.max_sampling_hz,
        "avg_ingestion_latency_ms": avg_latency_ms,
    }


@app.get("/processing/stream-plan")
async def processing_stream_plan(stream_count: int = 1200, asset_count: int = 30) -> dict[str, int]:
    return stream_processing_plan(stream_count=stream_count, asset_count=asset_count)
