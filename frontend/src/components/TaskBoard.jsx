import React from "react";

export function TaskBoard({ sensors = [] }) {
  if (!sensors.length) {
    return <div className="empty-block">No sensors registered for this asset.</div>;
  }

  return (
    <section className="sensor-board">
      {sensors.map((sensor) => (
        <article className="sensor-item" key={sensor.sensor_id}>
          <p className="sensor-type">{sensor.sensor_type}</p>
          <h4>{sensor.sensor_id}</h4>
          <p className="sensor-meta">
            {sensor.placement} • {sensor.sampling_hz} Hz
          </p>
          <p className="sensor-threshold">
            warning {sensor.threshold?.warning} / critical {sensor.threshold?.critical} {sensor.threshold?.unit}
          </p>
        </article>
      ))}
    </section>
  );
}
