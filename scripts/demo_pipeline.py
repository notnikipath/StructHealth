from __future__ import annotations

import json
import urllib.request
from datetime import UTC, datetime, timedelta

BASE = "http://localhost:8580"


def request(method: str, path: str, payload: dict | None = None) -> dict:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    now = datetime.now(UTC)
    readings = []
    for index in range(64):
        readings.append(
            {
                "sensor_id": "SNS-ACC-001",
                "asset_id": "AST-BRIDGE-001",
                "timestamp": (now + timedelta(milliseconds=index * 10)).isoformat(),
                "value": 0.58 + index * 0.015,
                "unit": "g",
                "sampling_hz": 100,
                "quality": 0.99,
                "metadata": {"channel": "z"},
            }
        )
    result = request(
        "POST",
        "/workflow/process-sensor-batch",
        {
            "asset_id": "AST-BRIDGE-001",
            "readings": readings,
            "source": "mqtt",
            "actor_id": "demo-script",
            "actor_role": "operator",
        },
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
