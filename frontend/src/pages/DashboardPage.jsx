import React, { useEffect, useMemo, useState } from "react";

import { KpiCard } from "../components/KpiCard";
import { TaskBoard } from "../components/TaskBoard";

const envGatewayUrl = import.meta.env.VITE_API_GATEWAY_URL?.trim();
const gatewayUrl =
  envGatewayUrl ||
  (typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:32071`
    : "http://localhost:32071");

const emptyPayload = {
  asset: { asset_id: "AST-BRIDGE-001", name: "Bridge", asset_type: "bridge", status: "operational" },
  sensors: { items: [] },
  readings: { items: [] },
  anomalies: { items: [], count: 0 },
  alerts: { items: [], count: 0 },
  report_today: { average_health_index: 100, anomalies_count: 0 },
  ingestion_metrics: { avg_polling_hz: 0, max_polling_hz_target: 100 },
  analysis_kpi: { actual_processing_latency_ms: 0, target_processing_latency_ms: 1000, forecast_accuracy_pct: 0, target_forecast_accuracy_pct: 90 },
  quality_summary: { forecast_accuracy_observed_pct: 0, processing_latency_observed_ms: 0 },
  notifications: { items: [] },
};

async function loadDashboard(assetId) {
  const response = await fetch(`${gatewayUrl}/dashboard/${assetId}?actor_role=engineer`);
  if (!response.ok) {
    throw new Error(`Failed to load dashboard: ${response.status}`);
  }
  return response.json();
}

function formatDate(value) {
  if (!value) return "n/a";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return "n/a";
  }
}

export function DashboardPage() {
  const [assetId, setAssetId] = useState("AST-BRIDGE-001");
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState(null);
  const [dashboard, setDashboard] = useState(emptyPayload);

  const refresh = async () => {
    try {
      setStatus("loading");
      const payload = await loadDashboard(assetId);
      setDashboard({ ...emptyPayload, ...payload });
      setStatus("live");
      setError(null);
    } catch (err) {
      setStatus("failed");
      setError(err.message);
    }
  };

  useEffect(() => {
    let mounted = true;
    loadDashboard(assetId)
      .then((payload) => {
        if (!mounted) return;
        setDashboard({ ...emptyPayload, ...payload });
        setStatus("live");
      })
      .catch((err) => {
        if (!mounted) return;
        setStatus("failed");
        setError(err.message);
      });
    return () => {
      mounted = false;
    };
  }, [assetId]);

  const latestReading = dashboard.readings?.items?.[dashboard.readings.items.length - 1];
  const healthIndex = Number(dashboard.report_today?.average_health_index || 100);
  const latency = Number(dashboard.analysis_kpi?.actual_processing_latency_ms || 0);
  const latencyTarget = Number(dashboard.analysis_kpi?.target_processing_latency_ms || 1000);
  const polling = Number(dashboard.ingestion_metrics?.avg_polling_hz || 0);
  const pollingTarget = Number(dashboard.ingestion_metrics?.max_polling_hz_target || 100);
  const forecastAccuracy = Number(dashboard.analysis_kpi?.forecast_accuracy_pct || 0);
  const forecastTarget = Number(dashboard.analysis_kpi?.target_forecast_accuracy_pct || 90);

  const headerStatus = useMemo(() => {
    if (status === "loading") return "loading";
    if (status === "failed") return "Service unavailable";
    return "live";
  }, [status]);

  return (
    <div className="app">
      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">StructHealth Monitoring</p>
          <h1>Infrastructure health</h1>
          <p>
            Real-time ingestion, FFT-based analysis, threshold breach detection, fatigue prediction, alerting, and daily
            expert reports.
          </p>
          <div className="hero-tags">
            <span>Sampling up to 100 Hz</span>
            <span>Latency under 1 second target</span>
            <span>Forecast accuracy target above 90%</span>
          </div>
        </div>
        <div className="hero-card">
          <label>
            Asset ID
            <input value={assetId} onChange={(event) => setAssetId(event.target.value)} placeholder="AST-BRIDGE-001" />
          </label>
          <button onClick={refresh} disabled={status === "loading"}>Refresh Dashboard</button>
          <p className="status-line" role="status" aria-live="polite">Status: {headerStatus}</p>
        </div>
      </header>

      <section className="kpi-grid">
        <KpiCard title="Health Index" value={`${healthIndex.toFixed(1)}`} hint="Keep above 75" isGood={healthIndex >= 75} />
        <KpiCard
          title="Processing Latency"
          value={`${latency.toFixed(1)} ms`}
          hint={`Target < ${latencyTarget} ms`}
          isGood={latency === 0 || latency <= latencyTarget}
        />
        <KpiCard
          title="Sampling Frequency"
          value={`${polling.toFixed(2)} Hz`}
          hint={`Target up to ${pollingTarget} Hz`}
          isGood={polling <= pollingTarget}
        />
        <KpiCard
          title="Forecast Accuracy"
          value={`${forecastAccuracy.toFixed(1)}%`}
          hint={`Target > ${forecastTarget}%`}
          isGood={forecastAccuracy >= forecastTarget}
        />
      </section>

      {error ? <div className="error">{error}</div> : null}

      <section className="content-grid">
        <article className="panel wide">
          <div className="panel-head">
            <div>
              <p className="section-label">Asset Passport</p>
              <h2>{dashboard.asset?.name}</h2>
            </div>
            <span className="pill">{dashboard.asset?.asset_type}</span>
          </div>
          <p>
            {dashboard.asset?.asset_id} · status: {dashboard.asset?.status} · built in {dashboard.asset?.built_year}
          </p>
          <TaskBoard sensors={dashboard.sensors?.items || []} />
        </article>

        <article className="panel">
          <div className="panel-head">
            <div>
              <p className="section-label">Latest Reading</p>
              <h2>Signal Pulse</h2>
            </div>
            <span className="pill">{dashboard.readings?.count || 0} samples</span>
          </div>
          <div className="stats-grid">
            <div>
              <strong>{latestReading ? latestReading.sensor_id : "n/a"}</strong>
              <span>sensor</span>
            </div>
            <div>
              <strong>{latestReading ? `${Number(latestReading.value).toFixed(3)} ${latestReading.unit}` : "n/a"}</strong>
              <span>value</span>
            </div>
            <div>
              <strong>{latestReading ? `${latestReading.sampling_hz} Hz` : "n/a"}</strong>
              <span>frequency</span>
            </div>
            <div>
              <strong>{latestReading ? formatDate(latestReading.timestamp) : "n/a"}</strong>
              <span>timestamp</span>
            </div>
          </div>
        </article>

        <article className="panel">
          <div className="panel-head">
            <div>
              <p className="section-label">Anomalies</p>
              <h2>Detection Feed</h2>
            </div>
            <span className="pill">{dashboard.anomalies?.count || 0}</span>
          </div>
          <div className="list">
            {(dashboard.anomalies?.items || []).slice(-5).reverse().map((item) => (
              <div className="list-item" key={item.event_id}>
                <div>
                  <p className="list-title">{item.code}</p>
                  <p className="list-sub">{item.message}</p>
                </div>
                <span>{item.severity}</span>
              </div>
            ))}
            {!dashboard.anomalies?.items?.length ? <div className="empty-block">No anomalies for selected period.</div> : null}
          </div>
        </article>

        <article className="panel">
          <div className="panel-head">
            <div>
              <p className="section-label">Alerts and Notifications</p>
              <h2>Response Queue</h2>
            </div>
            <span className="pill">{dashboard.alerts?.count || 0} alerts</span>
          </div>
          <div className="list">
            {(dashboard.alerts?.items || []).slice(-3).reverse().map((item) => (
              <div className="list-item" key={item.alert_id}>
                <div>
                  <p className="list-title">{item.title}</p>
                  <p className="list-sub">{item.message}</p>
                </div>
                <span>{item.severity}</span>
              </div>
            ))}
            {(dashboard.notifications?.items || []).slice(-2).reverse().map((item, index) => (
              <div className="list-item" key={`${item.subject}-${index}`}>
                <div>
                  <p className="list-title">{item.subject}</p>
                  <p className="list-sub">{item.body}</p>
                </div>
                <span>{item.channel}</span>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}
