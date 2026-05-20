from datetime import UTC, datetime, timedelta

from shared.structhealth_common import (
    Severity,
    apply_seismic_adjustment,
    asset_shard,
    classify_threshold,
    estimate_polling_hz,
    health_index,
    rolling_average,
)


def test_classify_threshold() -> None:
    assert classify_threshold(0.9, warning=0.7, critical=1.1) == Severity.WARNING
    assert classify_threshold(1.3, warning=0.7, critical=1.1) == Severity.CRITICAL
    assert classify_threshold(0.2, warning=0.7, critical=1.1) is None


def test_estimate_polling_hz() -> None:
    start = datetime.now(UTC)
    timestamps = [start + timedelta(milliseconds=i * 20) for i in range(10)]
    hz = estimate_polling_hz(timestamps)
    assert hz > 0


def test_health_and_seismic_adjustment() -> None:
    base = health_index(anomaly_density=0.2, fatigue_damage=0.18, max_threshold_ratio=0.6)
    assert 0 <= base <= 100
    adjusted = apply_seismic_adjustment(base, seismic_index=8.0)
    assert adjusted <= base


def test_shard_and_rolling_average() -> None:
    shard = asset_shard("AST-BRIDGE-001", shard_count=16)
    assert 0 <= shard < 16
    smoothed = rolling_average([1, 2, 3, 4, 5], window=3)
    assert len(smoothed) == 5
    assert smoothed[-1] > smoothed[0]
