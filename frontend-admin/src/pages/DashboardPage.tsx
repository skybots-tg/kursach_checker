import React, { useEffect, useState } from "react";
import { api, DashboardData } from "../api";

export const DashboardPage: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);
        console.log("[Dashboard] Loading dashboard data...");
        const dashboardData = await api.getDashboard();
        console.log("[Dashboard] Data loaded:", dashboardData);
        setData(dashboardData);
      } catch (err) {
        console.error("[Dashboard] Error loading data:", err);
        setError(err instanceof Error ? err.message : "Ошибка загрузки данных");
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="page-card">
        <div className="page-title">Дашборд</div>
        <div>Загрузка...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="page-card">
        <div className="page-title">Дашборд</div>
        <div style={{ color: "red" }}>Ошибка: {error || "Данные не загружены"}</div>
      </div>
    );
  }

  const formatTime = (seconds: number | null): string => {
    if (seconds === null) return "—";
    return `${Math.round(seconds)} с`;
  };

  const getStatusBadgeClass = (status: string): string => {
    if (status === "paid" || status === "done") return "badge badge-success";
    if (status === "error") return "badge badge-muted";
    return "badge";
  };

  return (
    <div className="page-grid">
      <section className="page-card">
        <div className="page-title">Дашборд</div>
        <div className="page-description">
          Ключевые показатели: проверки, оплаты, среднее время обработки, ошибки воркера.
        </div>
        <div className="kpi-row">
          <div className="kpi-card">
            <div className="kpi-label">Проверок за сегодня</div>
            <div className="kpi-value">{data.stats.checks_today}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Проверок за 7 дней</div>
            <div className="kpi-value">{data.stats.checks_7days}</div>
          </div>
        </div>
        <div className="kpi-row" style={{ marginTop: 10 }}>
          <div className="kpi-card">
            <div className="kpi-label">Успешных оплат за сегодня</div>
            <div className="kpi-value">{data.stats.payments_today}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Успешных оплат за 7 дней</div>
            <div className="kpi-value">{data.stats.payments_7days}</div>
          </div>
        </div>
        <div className="kpi-row" style={{ marginTop: 10 }}>
          <div className="kpi-card">
            <div className="kpi-label">Среднее время обработки</div>
            <div className="kpi-value">{formatTime(data.stats.avg_processing_time_seconds)}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Ошибки воркера (последние)</div>
            <div className="kpi-value">{data.stats.worker_errors_recent}</div>
          </div>
        </div>
      </section>
      <section className="page-card">
        <div className="section-title-row">
          <div className="section-title">Последние события</div>
          <div className="section-caption">Оплаты и проверки в хронологии</div>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Время</th>
              <th>Событие</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
            {data.recent_events.length === 0 ? (
              <tr>
                <td colSpan={3} style={{ textAlign: "center", color: "#999" }}>
                  Нет событий
                </td>
              </tr>
            ) : (
              data.recent_events.map((event, idx) => (
                <tr key={idx}>
                  <td>{event.time}</td>
                  <td>{event.event}</td>
                  <td>
                    <span className={getStatusBadgeClass(event.status)}>{event.status}</span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
};




