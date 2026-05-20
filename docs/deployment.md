# Deployment Notes

## Local prerequisites

- Docker + Docker Compose
- Python 3.11+
- Optional: Node 20+ for local frontend dev mode

## Start full stack

```bash
docker compose up --build -d
```

## Stop

```bash
docker compose down
```

## Ports

- `8580` gateway
- `5178` frontend
- `8501-8506` backend services
- `55445` PostgreSQL
- `55446` TimescaleDB
- `6390` Redis
- `19192` Redpanda Kafka

## Validation checks

```bash
python -m ruff check .
python -m pytest -q
docker compose config
```
