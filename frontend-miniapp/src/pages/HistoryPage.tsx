import React, { useEffect, useState } from "react";
import { fetchChecks, fetchOrders } from "../api";
import type { CheckItem, OrderItem } from "../types";
import { Link } from "react-router-dom";

export const HistoryPage: React.FC = () => {
  const [checks, setChecks] = useState<CheckItem[]>([]);
  const [orders, setOrders] = useState<OrderItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        const [cs, os] = await Promise.all([fetchChecks(), fetchOrders()]);
        if (!cancelled) {
          setChecks(cs);
          setOrders(os);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Не удалось загрузить историю");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="glass-card" style={{ padding: 16 }}>
      {loading ? (
        <div style={{ fontSize: 13 }}>Загружаем историю…</div>
      ) : error ? (
        <div style={{ fontSize: 13, color: "#b91c1c" }}>{error}</div>
      ) : (
        <>
          <div className="page-section-title">Проверки</div>
          <div className="card-list">
            {checks.map((c) => (
              <Link key={c.id} to={`/checks/${c.id}`} style={{ textDecoration: "none", color: "inherit" }}>
                <div className="finding-card">
                  <div className="finding-title-row">
                    <div className="finding-title">Проверка #{c.id}</div>
                    <span
                      className={`status-chip ${
                        c.status === "done"
                          ? "status-success"
                          : c.status === "error"
                          ? "status-error"
                          : "status-warning"
                      }`}
                    >
                      {c.status === "done"
                        ? "Готово"
                        : c.status === "error"
                        ? "Ошибка"
                        : c.status === "queued"
                        ? "В очереди"
                        : c.status === "running"
                        ? "Проверяется"
                        : c.status}
                    </span>
                  </div>
                  <div className="finding-meta">
                    Создано: {new Date(c.created_at).toLocaleString()}{" "}
                    {c.finished_at ? `· Завершено: ${new Date(c.finished_at).toLocaleString()}` : ""}
                  </div>
                </div>
              </Link>
            ))}
            {checks.length === 0 && <div className="page-section-description">Пока проверок не было.</div>}
          </div>

          <div className="spacer-16" />

          <div className="page-section-title">Оплаты</div>
          <div className="card-list">
            {orders.map((o) => (
              <div key={o.id} className="finding-card">
                <div className="finding-title-row">
                  <div className="finding-title">Заказ #{o.id}</div>
                  <span
                    className={`status-chip ${
                      o.status === "paid"
                        ? "status-success"
                        : o.status === "failed" || o.status === "cancelled"
                        ? "status-error"
                        : "status-warning"
                    }`}
                  >
                    {o.status}
                  </span>
                </div>
                <div className="finding-meta">
                  Сумма: {o.amount} · Создано: {new Date(o.created_at).toLocaleString()}
                  {o.paid_at ? ` · Оплачено: ${new Date(o.paid_at).toLocaleString()}` : ""}
                </div>
              </div>
            ))}
            {orders.length === 0 && <div className="page-section-description">Оплат пока не было.</div>}
          </div>
        </>
      )}
    </div>
  );
};



