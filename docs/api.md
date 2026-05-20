# API Overview

## Gateway

- `POST /auth/token`
- `POST /auth/verify`
- `GET /services/health`
- `POST /workflow/process-sensor-batch`
- `GET /dashboard/{asset_id}`
- `PUT /workflow/thresholds/{asset_id}/{sensor_id}`

## Asset service

- `GET /assets`
- `GET /assets/{asset_id}`
- `POST /assets`
- `GET /assets/{asset_id}/passport`
- `GET /assets/{asset_id}/sensors`
- `POST /assets/{asset_id}/sensors`
- `PUT /assets/{asset_id}/sensors/{sensor_id}/thresholds`
- `GET /assets/{asset_id}/sensor-layout`

## Ingestion service

- `POST /sensors/connect`
- `GET /sensors/connections`
- `POST /ingestion/batch`
- `GET /ingestion/readings/{asset_id}`
- `GET /ingestion/metrics`
- `GET /processing/stream-plan`

## Analysis service

- `PUT /analysis/thresholds`
- `POST /analysis/process-batch`
- `GET /analysis/anomalies/{asset_id}`
- `GET /analysis/trends/{asset_id}`
- `POST /analysis/seismic/merge`
- `GET /analysis/kpi`

## Alert service

- `POST /alerts/raise`
- `POST /alerts/fatigue-forecast`
- `GET /alerts/{asset_id}`
- `POST /alerts/{asset_id}/{alert_id}/ack`

## Report service

- `POST /reports/daily/update`
- `GET /reports/daily/{asset_id}`
- `GET /reports/trends/{asset_id}`
- `GET /reports/export/{asset_id}`
- `GET /reports/summary`

## Notification service

- `POST /notify/send`
- `POST /notify/critical`
- `GET /notify/history`
