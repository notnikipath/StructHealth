from __future__ import annotations

from math import cos, sin, sqrt

try:
    import numpy as np
except Exception:  # pragma: no cover - optional dependency fallback
    np = None  # type: ignore[assignment]

try:
    from scipy.signal import butter, filtfilt
except Exception:  # pragma: no cover - optional dependency fallback
    butter = None  # type: ignore[assignment]
    filtfilt = None  # type: ignore[assignment]

try:
    from sklearn.linear_model import LinearRegression
except Exception:  # pragma: no cover - optional dependency fallback
    LinearRegression = None  # type: ignore[assignment]


def lowpass_filter(values: list[float], cutoff_hz: float, sampling_hz: float, order: int = 3) -> list[float]:
    if len(values) < 4:
        return values
    cutoff_hz = max(0.1, cutoff_hz)
    sampling_hz = max(1.0, sampling_hz)
    if np is not None and butter is not None and filtfilt is not None:
        nyquist = sampling_hz / 2.0
        normalized = min(max(cutoff_hz / max(nyquist, 1e-6), 0.001), 0.99)
        b, a = butter(order, normalized, btype="low", analog=False)
        padlen = min(3 * max(len(a), len(b)), len(values) - 2)
        return filtfilt(b, a, np.asarray(values, dtype=float), padlen=padlen).tolist()
    window = min(max(int(sampling_hz // max(cutoff_hz, 1)), 2), 12)
    filtered: list[float] = []
    for index in range(len(values)):
        start = max(0, index - window + 1)
        segment = values[start : index + 1]
        filtered.append(sum(segment) / len(segment))
    return filtered


def fft_spectrum(values: list[float], sampling_hz: float) -> list[dict[str, float]]:
    if len(values) < 2:
        return []
    if np is not None:
        arr = np.asarray(values, dtype=float)
        centered = arr - float(np.mean(arr))
        freq = np.fft.rfftfreq(centered.size, d=1.0 / max(sampling_hz, 1.0))
        amp = np.abs(np.fft.rfft(centered))
        result = []
        for f, a in zip(freq, amp, strict=True):
            result.append({"frequency_hz": float(f), "amplitude": float(a)})
        return result
    result: list[dict[str, float]] = []
    n = len(values)
    centered = [value - sum(values) / n for value in values]
    for k in range(n // 2 + 1):
        real = 0.0
        imag = 0.0
        for t, sample in enumerate(centered):
            angle = 2 * 3.14159265359 * k * t / n
            real += sample * cos(angle)
            imag -= sample * sin(angle)
        amplitude = sqrt(real * real + imag * imag)
        frequency = k * sampling_hz / n
        result.append({"frequency_hz": frequency, "amplitude": amplitude})
    return result


def dominant_frequency(values: list[float], sampling_hz: float) -> float:
    spectrum = fft_spectrum(values, sampling_hz)
    if not spectrum:
        return 0.0
    non_dc = [item for item in spectrum if item["frequency_hz"] > 0]
    if not non_dc:
        return 0.0
    peak = max(non_dc, key=lambda item: item["amplitude"])
    return round(float(peak["frequency_hz"]), 3)


def anomaly_score(values: list[float]) -> float:
    if not values:
        return 0.0
    if np is not None:
        arr = np.asarray(values, dtype=float)
        std = float(np.std(arr))
        if std <= 1e-9:
            return 0.0
        z_max = float(np.max(np.abs((arr - float(np.mean(arr))) / std)))
        drift = abs(float(arr[-1] - arr[0])) / (abs(float(np.mean(arr))) + 1e-6)
        return round(min(1.0, z_max / 6 + drift / 3), 3)
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    std = sqrt(variance)
    if std <= 1e-9:
        return 0.0
    z_max = max(abs((value - mean) / std) for value in values)
    drift = abs(values[-1] - values[0]) / (abs(mean) + 1e-6)
    return round(min(1.0, z_max / 6 + drift / 3), 3)


def fatigue_damage_index(values: list[float], design_limit: float = 1.0) -> float:
    if not values:
        return 0.0
    limit = max(abs(design_limit), 1e-6)
    damage = sum((abs(value) / limit) ** 3 for value in values) / len(values)
    return round(damage, 5)


def predict_residual_life_days(
    damage_history: list[float],
    days_observed: int = 30,
    failure_damage: float = 1.0,
    max_horizon_days: int = 3650,
) -> float:
    if len(damage_history) < 2:
        return float(max_horizon_days)
    horizon = max(len(damage_history), days_observed)
    x = list(range(len(damage_history)))
    y = damage_history
    if LinearRegression is not None and np is not None:
        model = LinearRegression()
        model.fit(np.asarray(x).reshape(-1, 1), np.asarray(y))
        slope = float(model.coef_[0])
        current = float(y[-1])
    else:
        slope = (y[-1] - y[0]) / max(len(y) - 1, 1)
        current = y[-1]
    if slope <= 0:
        return float(max_horizon_days)
    remaining = max((failure_damage - current) / slope, 0)
    forecast = min(max_horizon_days, horizon + remaining)
    return round(float(forecast), 2)


def stream_processing_plan(stream_count: int, asset_count: int) -> dict[str, int]:
    workers = min(48, max(2, asset_count * 2, stream_count // 120))
    batch_size = max(32, stream_count // max(1, workers))
    return {"workers": workers, "batch_size": batch_size, "stream_count": stream_count}


def forecast_accuracy_score(predictions: list[float], actuals: list[float]) -> float:
    if not predictions or not actuals or len(predictions) != len(actuals):
        return 0.0
    errors = []
    for predicted, actual in zip(predictions, actuals, strict=True):
        if actual <= 0:
            continue
        errors.append(abs((actual - predicted) / actual))
    if not errors:
        return 0.0
    mape = sum(errors) / len(errors)
    accuracy = max(0.0, 1.0 - mape)
    return round(accuracy * 100, 2)
