from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "structhealth-service"
    service_port: int = 8500
    environment: str = "dev"

    postgres_dsn: str = "postgresql+psycopg://structhealth:structhealth@postgres:5432/structhealth"
    redis_url: str = "redis://redis:6379/0"
    timescale_dsn: str = "postgresql+psycopg://structhealth:structhealth@timescaledb:5432/structhealth"
    kafka_bootstrap_servers: str = "redpanda:9092"
    mqtt_broker_url: str = "mqtt://mosquitto:1883"

    jwt_secret: str = "structhealth-dev-secret"
    encryption_key: str = "structhealth-dev-encryption-key"

    max_sampling_hz: int = 100
    processing_latency_target_ms: int = 1000
    defect_forecast_accuracy_target: float = 90.0
    analysis_threshold_cache_ttl_seconds: int = 120
    ingestion_stream_shards: int = 16

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
