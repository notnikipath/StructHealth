from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from .schemas import Severity


def classify_threshold(value: float, warning: float, critical: float, direction: str = "above") -> Severity | None:
    if direction == "above":
        if value >= critical:
            return Severity.CRITICAL
        if value >= warning:
            return Severity.WARNING
    elif direction == "below":
        if value <= critical:
            return Severity.CRITICAL
        if value <= warning:
            return Severity.WARNING
    else:
        abs_value = abs(value)
        if abs_value >= abs(critical):
            return Severity.CRITICAL
        if abs_value >= abs(warning):
            return Severity.WARNING
    return None


def estimate_polling_hz(timestamps: list[datetime]) -> float:
    if len(timestamps) < 2:
        return 0.0
    ordered = sorted(ts if ts.tzinfo else ts.replace(tzinfo=UTC) for ts in timestamps)
    deltas = []
    for index in range(1, len(ordered)):
        delta_s = (ordered[index] - ordered[index - 1]).total_seconds()
        if delta_s > 0:
            deltas.append(delta_s)
    if not deltas:
        return 0.0
    average_delta = sum(deltas) / len(deltas)
    if average_delta <= 0:
        return 0.0
    return round(1.0 / average_delta, 2)


def health_index(anomaly_density: float, fatigue_damage: float, max_threshold_ratio: float) -> float:
    anomaly_penalty = min(max(anomaly_density, 0), 1) * 45
    fatigue_penalty = min(max(fatigue_damage, 0), 2) * 25
    threshold_penalty = min(max(max_threshold_ratio, 0), 2) * 20
    value = 100 - anomaly_penalty - fatigue_penalty - threshold_penalty
    return round(min(max(value, 0), 100), 2)


def apply_seismic_adjustment(base_score: float, seismic_index: float) -> float:
    normalized = min(max(seismic_index, 0), 10)
    penalty = normalized * 2.5
    return round(min(max(base_score - penalty, 0), 100), 2)


def asset_shard(asset_id: str, shard_count: int) -> int:
    if shard_count <= 1:
        return 0
    digest = hashlib.sha256(asset_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % shard_count


def rolling_average(values: list[float], window: int = 5) -> list[float]:
    if window <= 1 or len(values) <= 1:
        return values
    result: list[float] = []
    for index in range(len(values)):
        start = max(0, index - window + 1)
        segment = values[start : index + 1]
        result.append(sum(segment) / len(segment))
    return result
