# Architecture

## Scope

StructHealth monitors critical civil structures and processes high-frequency sensor streams for vibration, tilt, strain, and crack growth risk.

## Service map

- `api-gateway`: entry point, auth token issuance, workflow orchestration, dashboard aggregation
- `asset-service`: asset passport, coordinates, construction metadata, sensor map
- `ingestion-service`: sensor connection registry, real-time ingest, shard routing, async write queue
- `analysis-service`: signal filtering, FFT features, threshold checks, anomaly detection, fatigue forecast
- `alert-service`: operational alerts, critical escalation and acknowledgement
- `report-service`: daily summaries, trend views, expert export
- `notification-service`: outbound alerts through SMS, email, push, webhook

## Infrastructure

- PostgreSQL for operational metadata
- TimescaleDB for sensor time-series persistence (service-ready integration point)
- Redis for short-term cache and coordination
- Redpanda for Kafka-compatible event streaming
- Docker Compose for local deployment

## Core workflow

1. Sensor batch arrives at `api-gateway`
2. `ingestion-service` validates and stores batch asynchronously
3. `analysis-service` applies filtering + FFT + anomaly/fatigue logic
4. `alert-service` creates incident when risk is elevated
5. `notification-service` sends critical notifications
6. `report-service` updates daily statistics and trends

## Scalability notes

- Ingestion sharding by `asset_id`
- Async queue-backed write path
- Threshold cache with TTL to reduce repeated reads
- Stream processing plan endpoint to size workers for load tests
