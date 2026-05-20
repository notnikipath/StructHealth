from shared.structhealth_common import (
    anomaly_score,
    dominant_frequency,
    fatigue_damage_index,
    forecast_accuracy_score,
    lowpass_filter,
    predict_residual_life_days,
    stream_processing_plan,
)


def test_lowpass_filter_returns_values() -> None:
    values = [0.1, 0.15, 0.2, 0.7, 0.75, 0.72, 0.2]
    filtered = lowpass_filter(values, cutoff_hz=10, sampling_hz=100)
    assert len(filtered) == len(values)


def test_anomaly_score_and_frequency() -> None:
    normal_signal = [0.2, 0.22, 0.21, 0.2, 0.23, 0.24]
    disturbed_signal = [0.2, 0.22, 0.21, 0.8, 1.0, 0.9]
    assert anomaly_score(disturbed_signal) > anomaly_score(normal_signal)
    assert dominant_frequency([0, 1, 0, -1] * 8, sampling_hz=32) >= 0


def test_fatigue_and_residual_life() -> None:
    damage = fatigue_damage_index([0.1, 0.3, 0.5, 0.7], design_limit=1.0)
    assert damage > 0
    residual = predict_residual_life_days([0.1, 0.2, 0.3, 0.42], days_observed=30)
    assert residual > 0


def test_stream_plan_and_accuracy() -> None:
    plan = stream_processing_plan(stream_count=5400, asset_count=12)
    assert plan["workers"] >= 2
    assert plan["batch_size"] >= 32
    accuracy = forecast_accuracy_score([10, 12, 8], [11, 12, 8])
    assert 0 <= accuracy <= 100
