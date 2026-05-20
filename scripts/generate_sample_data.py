from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

ASSETS = [
    ("AST-BRIDGE-001", "bridge"),
    ("AST-HRB-004", "highrise_building"),
    ("AST-DAM-002", "dam"),
    ("AST-TUN-007", "tunnel"),
    ("AST-CHM-010", "industrial_chimney"),
]
SENSORS = [
    ("SNS-ACC-001", "accelerometer", "g", 100),
    ("SNS-INC-001", "inclinometer", "deg", 20),
    ("SNS-CRK-001", "crack_meter", "mm", 5),
    ("SNS-STR-001", "strain_gauge", "microstrain", 50),
]


def generate_record(index: int) -> dict:
    asset_id, asset_type = random.choice(ASSETS)
    sensor_id, sensor_type, unit, sampling_hz = random.choice(SENSORS)
    timestamp = datetime.now(UTC) - timedelta(milliseconds=index * 10)
    base = {
        "accelerometer": random.uniform(0.05, 0.8),
        "inclinometer": random.uniform(0.01, 0.2),
        "crack_meter": random.uniform(0.2, 2.8),
        "strain_gauge": random.uniform(60, 920),
    }[sensor_type]
    if random.random() < 0.006:
        base *= random.uniform(1.7, 2.8)
    return {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "sensor_id": sensor_id,
        "sensor_type": sensor_type,
        "timestamp": timestamp.isoformat(),
        "value": round(base, 5),
        "unit": unit,
        "sampling_hz": sampling_hz,
        "quality": round(random.uniform(0.92, 1.0), 3),
        "source": "mqtt",
    }


if __name__ == "__main__":
    random.seed(28)
    output = Path(__file__).resolve().parents[1] / "data" / "samples" / "structhealth_events.json"
    payload = [generate_record(index) for index in range(1, 12001)]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload)} records to {output}")
