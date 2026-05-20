import React from "react";

export function KpiCard({ title, value, hint, isGood = true }) {
  return (
    <article className="kpi-card">
      <p className="kpi-title">{title}</p>
      <p className="kpi-value">{value}</p>
      <p className={`kpi-hint ${isGood ? "good" : "bad"}`}>{hint}</p>
    </article>
  );
}
