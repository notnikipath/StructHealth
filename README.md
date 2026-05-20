# StructHealth

StructHealth is a microservice platform for structural health monitoring of bridges, high-rise buildings, dams, tunnels, and industrial chimneys.

## Modules

- `api-gateway` - workflow orchestration and unified dashboard API
- `asset-service` - asset passport and sensor layout
- `ingestion-service` - sensor connectivity and real-time batch ingestion
- `analysis-service` - FFT/filtering, anomaly detection, fatigue forecast
- `alert-service` - critical alerts and risk escalation
- `report-service` - daily reports, trends, export for experts
- `notification-service` - message delivery for engineers and emergency responders
- `frontend` - monitoring dashboard UI

## Stack

- Backend: Python FastAPI
- Databases: PostgreSQL, TimescaleDB, Redis
- Queue/stream: Redpanda (Kafka-compatible), MQTT-ready ingestion endpoints
- Analytics: NumPy, SciPy, scikit-learn
- Frontend: React + Vite

## Optional improvements implemented

- Group A: residual life forecast (ML-style trend regression)
- Group C: streaming plan, parameter caching, asset sharding, async queue-based writes
- Group B: coordinate-based asset model ready for GPS/GLONASS integrations

## Quality targets

- Sensor polling up to `100 Hz`
- Processing latency target `< 1 sec`
- Defect forecast accuracy target `> 90%`

## Run

```bash
cd 'your/project/folder'
docker compose up --build -d
```

## Useful URLs

- Frontend: `http://localhost:5178`
- Gateway health: `http://localhost:8580/health`
- Services health: `http://localhost:8580/services/health`
- Swagger: `http://localhost:8580/docs`

## Validation

```bash
python -m ruff check .
python -m pytest -q
docker compose config
```

## Demo workflow

```bash
python scripts/demo_pipeline.py
```

## Sample data

Generate 12k sensor events:

```bash
python scripts/generate_sample_data.py
```

Result file: `data/samples/structhealth_events.json`
