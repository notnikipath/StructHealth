# Algorithms

## Signal processing

- Low-pass filtering (`lowpass_filter`) for noise suppression before feature extraction
- FFT-based dominant frequency extraction (`fft_spectrum`, `dominant_frequency`)
- Robust anomaly score from z-score peak and short-term drift (`anomaly_score`)

## Safety checks

- Threshold classification with directional logic (`classify_threshold`)
- Alert severity mapping from threshold breach or high anomaly score

## Fatigue and residual life

- Simplified fatigue damage accumulation (`fatigue_damage_index`)
- Rolling smoothing of damage history (`rolling_average`)
- Residual life trend forecast (`predict_residual_life_days`) using linear model fallback

## Health KPI

- Composite health index from anomaly density, fatigue damage, and threshold ratio (`health_index`)
- Optional seismic penalty (`apply_seismic_adjustment`)

## Throughput/scaling

- Shard selection by asset hash (`asset_shard`)
- Worker sizing plan for streaming load (`stream_processing_plan`)
