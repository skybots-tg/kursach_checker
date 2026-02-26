import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { fetchCheckDetail } from "../api";
import type { CheckDetailResponse, CheckReportFinding } from "../types";

type Filter = "all" | "errors" | "warnings" | "autofixed" | "advice";

export const CheckResultPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<CheckDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        const res = await fetchCheckDetail(Number(id));
        if (!cancelled) setData(res);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Не удалось загрузить результат");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  const findings: CheckReportFinding[] = data?.report?.findings || [];

  const filteredFindings = findings.filter((f) => {
    if (filter === "all") return true;
    if (filter === "errors") return f.severity === "error";
    if (filter === "warnings") return f.severity === "warning";
    if (filter === "autofixed") return !!f.auto_fixed;
    if (filter === "advice") return f.severity === "advice" || f.severity === "info";
    return true;
  });

  const errorsCount = data?.report?.summary_errors ?? findings.filter((f) => f.severity === "error").length;
  const warningsCount = data?.report?.summary_warnings ?? findings.filter((f) => f.severity === "warning").length;
  const autofixedCount =
    data?.report?.summary_autofixed ?? findings.filter((f) => f.auto_fixed && f.severity !== "error").length;

  return (
    <div className="glass-card" style={{ padding: 16 }}>
      {loading ? (
        <div style={{ fontSize: 13 }}>Загружаем результат проверки…</div>
      ) : error ? (
        <div style={{ fontSize: 13, color: "#b91c1c" }}>{error}</div>
      ) : !data ? (
        <div style={{ fontSize: 13 }}>Результат не найден.</div>
      ) : (
        <>
          <div className="page-section-title">Результат проверки #{data.id}</div>
          <div className="page-section-description">
            Статус:{" "}
            {data.status === "done"
              ? "Готово"
              : data.status === "error"
              ? "Ошибка"
              : data.status === "queued"
              ? "В очереди"
              : data.status === "running"
              ? "Проверяется"
              : data.status}
          </div>

          <div className="kpi-row">
            <div className="kpi-card">
              <div className="kpi-label">Ошибки</div>
              <div className="kpi-value" style={{ color: "#b91c1c" }}>{errorsCount}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Предупреждения</div>
              <div className="kpi-value" style={{ color: "#92400e" }}>{warningsCount}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Автоисправлено</div>
              <div className="kpi-value" style={{ color: "#065f46" }}>{autofixedCount}</div>
            </div>
          </div>

          <div className="spacer-12" />

          <div className="filters-row">
            <button
              className={`filter-pill ${filter === "all" ? "filter-pill-active" : ""}`}
              onClick={() => setFilter("all")}
            >
              Все
            </button>
            <button
              className={`filter-pill ${filter === "errors" ? "filter-pill-active" : ""}`}
              onClick={() => setFilter("errors")}
            >
              Ошибки
            </button>
            <button
              className={`filter-pill ${filter === "warnings" ? "filter-pill-active" : ""}`}
              onClick={() => setFilter("warnings")}
            >
              Предупреждения
            </button>
            <button
              className={`filter-pill ${filter === "autofixed" ? "filter-pill-active" : ""}`}
              onClick={() => setFilter("autofixed")}
            >
              Исправлено
            </button>
            <button
              className={`filter-pill ${filter === "advice" ? "filter-pill-active" : ""}`}
              onClick={() => setFilter("advice")}
            >
              Советы
            </button>
          </div>

          <div className="card-list">
            {filteredFindings.map((f) => (
              <div key={f.rule_id} className="finding-card">
                <div className="finding-title-row">
                  <div className="finding-title">{f.title}</div>
                  <span
                    className={`status-chip ${
                      f.severity === "error"
                        ? "status-error"
                        : f.severity === "warning"
                        ? "status-warning"
                        : f.auto_fixed
                        ? "status-success"
                        : "status-info"
                    }`}
                  >
                    {f.severity === "error"
                      ? "Ошибка"
                      : f.severity === "warning"
                      ? "Предупреждение"
                      : f.auto_fixed
                      ? "Исправлено"
                      : "Совет"}
                  </span>
                </div>
                <div className="finding-meta">
                  {f.category}{" "}
                  {f.location?.section_id ? `· раздел: ${f.location.section_id || f.location.section_title}` : null}
                </div>
                {f.expected && <div className="finding-text">Ожидалось: {f.expected}</div>}
                {f.actual && (
                  <div className="finding-text text-muted">
                    Факт: <span>{f.actual}</span>
                  </div>
                )}
                {f.recommendation && (
                  <div className="finding-text" style={{ marginTop: 4 }}>
                    <strong>Рекомендация:</strong> {f.recommendation}
                  </div>
                )}
              </div>
            ))}
            {filteredFindings.length === 0 && (
              <div className="page-section-description">Нарушений не обнаружено или отчёт ещё формируется.</div>
            )}
          </div>
        </>
      )}
    </div>
  );
};


