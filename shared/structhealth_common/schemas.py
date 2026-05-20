from __future__ import annotations

from datetime import UTC, date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    BRIDGE = "bridge"
    HIGHRISE_BUILDING = "highrise_building"
    DAM = "dam"
    TUNNEL = "tunnel"
    INDUSTRIAL_CHIMNEY = "industrial_chimney"


class SensorType(str, Enum):
    ACCELEROMETER = "accelerometer"
    STRAIN_GAUGE = "strain_gauge"
    INCLINOMETER = "inclinometer"
    CRACK_METER = "crack_meter"
    TEMPERATURE = "temperature"
    SEISMIC = "seismic"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Role(str, Enum):
    OPERATOR = "operator"
    ENGINEER = "engineer"
    INSPECTOR = "inspector"
    ADMIN = "admin"
    EMERGENCY = "emergency"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    TELEGRAM = "telegram"
    PUSH = "push"
    WEBHOOK = "webhook"


class GeoPoint(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    elevation_m: float = 0


class SensorThreshold(BaseModel):
    warning: float
    critical: float
    direction: str = Field(default="above", pattern="^(above|below|both)$")
    unit: str
    fatigue_limit: float | None = None


class SensorNode(BaseModel):
    sensor_id: str
    asset_id: str
    sensor_type: SensorType
    placement: str
    axis: str | None = None
    sampling_hz: float = Field(gt=0, le=100)
    calibration_offset: float = 0
    threshold: SensorThreshold
    enabled: bool = True
    installed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AssetPassport(BaseModel):
    asset_id: str
    name: str
    asset_type: AssetType
    coordinates: GeoPoint
    built_year: int = Field(ge=1800, le=2100)
    materials: list[str] = Field(default_factory=list)
    design_life_years: int = Field(gt=0)
    owner: str
    status: str = "operational"
    sensors: list[SensorNode] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AssetCreateRequest(BaseModel):
    name: str
    asset_type: AssetType
    coordinates: GeoPoint
    built_year: int = Field(ge=1800, le=2100)
    materials: list[str] = Field(default_factory=list)
    design_life_years: int = Field(gt=0, default=100)
    owner: str
    actor_id: str
    actor_role: Role


class SensorRegistrationRequest(BaseModel):
    sensor_type: SensorType
    placement: str
    axis: str | None = None
    sampling_hz: float = Field(gt=0, le=100)
    calibration_offset: float = 0
    threshold: SensorThreshold
    actor_id: str
    actor_role: Role


class SensorReading(BaseModel):
    sensor_id: str
    asset_id: str
    timestamp: datetime
    value: float
    unit: str
    sampling_hz: float = Field(gt=0, le=100)
    quality: float = Field(default=1.0, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SensorBatchIngestRequest(BaseModel):
    asset_id: str
    readings: list[SensorReading] = Field(default_factory=list)
    source: str = "mqtt"
    actor_id: str = "system"
    actor_role: Role = Role.OPERATOR


class SignalSummary(BaseModel):
    sensor_id: str
    sample_count: int
    mean_value: float
    rms_value: float
    peak_value: float
    dominant_frequency_hz: float
    anomaly_score: float
    threshold_breached: bool
    fatigue_damage: float
    residual_life_days: float


class AnomalyEvent(BaseModel):
    event_id: str
    asset_id: str
    sensor_id: str
    severity: Severity
    code: str
    message: str
    observed_value: float
    threshold_value: float | None = None
    anomaly_score: float = Field(ge=0, le=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BatchAnalysisResponse(BaseModel):
    asset_id: str
    processed_readings: int
    processing_latency_ms: float
    target_processing_latency_ms: int = 1000
    anomalies: list[AnomalyEvent] = Field(default_factory=list)
    summaries: list[SignalSummary] = Field(default_factory=list)


class AlertRecord(BaseModel):
    alert_id: str
    asset_id: str
    severity: Severity
    title: str
    message: str
    anomaly_ids: list[str] = Field(default_factory=list)
    predicted_failure_days: float | None = None
    status: str = "open"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AlertCreateRequest(BaseModel):
    asset_id: str
    anomalies: list[AnomalyEvent] = Field(default_factory=list)
    residual_life_days: float | None = None
    actor_id: str
    actor_role: Role


class DailyAssetStats(BaseModel):
    asset_id: str
    report_date: date
    readings_count: int = 0
    anomalies_count: int = 0
    max_vibration: float = 0
    max_tilt_deg: float = 0
    max_crack_mm: float = 0
    average_health_index: float = Field(default=100, ge=0, le=100)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReportUpdateRequest(BaseModel):
    asset_id: str
    readings_count: int
    anomalies_count: int
    max_vibration: float = 0
    max_tilt_deg: float = 0
    max_crack_mm: float = 0
    average_health_index: float = Field(ge=0, le=100)
    actor_id: str
    actor_role: Role


class NotificationPayload(BaseModel):
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    severity: Severity = Severity.INFO
    actor_role: Role = Role.ENGINEER
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AuditEvent(BaseModel):
    event_id: str
    actor_id: str
    actor_role: Role | str
    action: str
    object_type: str
    object_id: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProcessSensorBatchResult(BaseModel):
    ingestion: dict[str, Any]
    analysis: dict[str, Any]
    alerts: list[dict[str, Any]] = Field(default_factory=list)
    report: dict[str, Any]
    processed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
