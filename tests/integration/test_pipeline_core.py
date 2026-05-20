from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from tests.integration.helpers import load_module

ROOT = Path(__file__).resolve().parents[2]

asset_module = load_module("asset_module", ROOT / "asset-service" / "app" / "main.py")
ingestion_module = load_module("ingestion_module", ROOT / "ingestion-service" / "app" / "main.py")
analysis_module = load_module("analysis_module", ROOT / "analysis-service" / "app" / "main.py")
alert_module = load_module("alert_module", ROOT / "alert-service" / "app" / "main.py")
report_module = load_module("report_module", ROOT / "report-service" / "app" / "main.py")
notification_module = load_module("notification_module", ROOT / "notification-service" / "app" / "main.py")

asset_client = TestClient(asset_module.app)
ingestion_client = TestClient(ingestion_module.app)
analysis_client = TestClient(analysis_module.app)
alert_client = TestClient(alert_module.app)
report_client = TestClient(report_module.app)
notification_client = TestClient(notification_module.app)


def _build_readings() -> list[dict]:
    now = datetime.now(UTC)
    items = []
    for idx in range(48):
        items.append(
            {
                "sensor_id": "SNS-ACC-001",
                "asset_id": "AST-BRIDGE-001",
                "timestamp": (now + timedelta(milliseconds=idx * 10)).isoformat(),
                "value": 0.45 + idx * 0.02,
                "unit": "g",
                "sampling_hz": 100,
                "quality": 0.99,
            }
        )
    return items


def test_asset_ingestion_analysis_alert_report_flow() -> None:
    asset = asset_client.get("/assets/AST-BRIDGE-001", params={"actor_role": "operator"})
    assert asset.status_code == 200
    assert asset.json()["asset_type"] == "bridge"

    threshold = analysis_client.put(
        "/analysis/thresholds",
        json={
            "asset_id": "AST-BRIDGE-001",
            "sensor_id": "SNS-ACC-001",
            "threshold": {"warning": 0.7, "critical": 1.05, "direction": "above", "unit": "g", "fatigue_limit": 1.2},
            "actor_id": "ENG-001",
            "actor_role": "engineer",
        },
    )
    assert threshold.status_code == 200

    ingestion = ingestion_client.post(
        "/ingestion/batch",
        json={
            "asset_id": "AST-BRIDGE-001",
            "readings": _build_readings(),
            "source": "mqtt",
            "actor_id": "OP-001",
            "actor_role": "operator",
        },
    )
    assert ingestion.status_code == 200
    assert ingestion.json()["accepted"] == 48

    analysis = analysis_client.post(
        "/analysis/process-batch",
        json={
            "asset_id": "AST-BRIDGE-001",
            "readings": _build_readings(),
            "source": "mqtt",
            "actor_id": "ENG-001",
            "actor_role": "engineer",
        },
    )
    assert analysis.status_code == 200
    payload = analysis.json()
    assert payload["processed_readings"] == 48
    assert payload["summaries"]

    alert = alert_client.post(
        "/alerts/raise",
        json={
            "asset_id": "AST-BRIDGE-001",
            "anomalies": payload["anomalies"],
            "residual_life_days": min(item["residual_life_days"] for item in payload["summaries"]),
            "actor_id": "ENG-001",
            "actor_role": "engineer",
        },
    )
    assert alert.status_code == 200

    report = report_client.post(
        "/reports/daily/update",
        json={
            "asset_id": "AST-BRIDGE-001",
            "readings_count": payload["processed_readings"],
            "anomalies_count": len(payload["anomalies"]),
            "max_vibration": 1.2,
            "max_tilt_deg": 0.0,
            "max_crack_mm": 0.0,
            "average_health_index": payload["asset_health_index"],
            "actor_id": "ENG-001",
            "actor_role": "engineer",
        },
    )
    assert report.status_code == 200

    notify = notification_client.post(
        "/notify/critical",
        json={
            "asset_id": "AST-BRIDGE-001",
            "recipient": "oncall@structhealth.local",
            "issue": "Critical vibration trend detected",
            "actor_role": "engineer",
        },
    )
    assert notify.status_code == 200
