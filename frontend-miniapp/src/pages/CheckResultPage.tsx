import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { fetchCheckDetail, getDownloadUrl } from "../api";
import type { CheckDetailResponse, CheckReportFinding } from "../types";

type Filter = "all" | "errors" | "warnings" | "autofixed" | "advice";

const POLL_INTERVAL_MS = 3000;

export const CheckResultPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<CheckDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const res = await fetchCheckDetail(Number(id));
      setData(res);
      setError(null);
      return res;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить результат");
      return null;
    }
  }, [id]);

  useEffect(() => {
    let cancelled = false;

    async function initialLoad() {
      setLoading(true);
      const res = await load();
      if (cancelled) return;
      setLoading(false);
      if (res && (res.status === "queued" || res.status === "running")) {
        schedulePoll();
      }
    }

    function schedulePoll() {
      timerRef.current = setTimeout(async () => {
        if (cancelled) return;
        const res = await load();
        if (cancelled) return;
        if (res && (res.status === "queued" || res.status === "running")) {
          schedulePoll();
        }
      }, POLL_INTERVAL_MS);
    }

    void initialLoad();
    return () => {
      cancelled = true;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [load]);

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

  const isPending = data?.status === "queued" || data?.status === "running";

  return (
    <div className="glass-card" style={{ padding: "var(--spacing-lg)" }}>
      {loading ? (
        <div style={{ fontSize: "var(--font-size-sm)" }}>Загружаем результат проверки…</div>
      ) : error ? (
        <div style={{ fontSize: "var(--font-size-sm)", color: "var(--accent-error)" }}>{error}</div>
      ) : !data ? (
        <div style={{ fontSize: "var(--font-size-sm)" }}>Результат не найден.</div>
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
              ? "Проверяется…"
              : data.status}
            {isPending && <span style={{ marginLeft: 8, fontSize: "var(--font-size-xs)" }}>(обновляется автоматически)</span>}
          </div>

          {!isPending && (
            <>
              <div className="kpi-row">
                <div className="kpi-card">
                  <div className="kpi-label">Ошибки</div>
                  <div className="kpi-value" style={{ color: "var(--accent-error)" }}>{errorsCount}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Предупреждения</div>
                  <div className="kpi-value" style={{ color: "var(--accent-warning)" }}>{warningsCount}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Автоисправлено</div>
                  <div className="kpi-value" style={{ color: "var(--accent-success)" }}>{autofixedCount}</div>
                </div>
              </div>

              {(data.output_file_id || data.report_file_id) && (
                <>
                  <div className="spacer-12" />
                  <div style={{ display: "flex", gap: "var(--spacing-sm)" }}>
                    {data.output_file_id && (
                      <a
                        href={getDownloadUrl(data.output_file_id)}
                        style={{ flex: 1, textDecoration: "none" }}
                      >
                        <button className="primary-btn" style={{ width: "100%" }}>
                          Скачать исправленный документ
                        </button>
                      </a>
                    )}
                    {data.report_file_id && (
                      <a
                        href={getDownloadUrl(data.report_file_id)}
                        style={{ flex: 1, textDecoration: "none" }}
                      >
                        <button className="secondary-btn" style={{ width: "100%" }}>
                          Скачать отчёт (JSON)
                        </button>
                      </a>
                    )}
                  </div>
                </>
              )}

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
                {filteredFindings.map((f, idx) => (
                  <div key={idx} className="finding-card">
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
                      {f.category}
                      {f.location ? ` · ${f.location}` : null}
                    </div>
                    {f.expected && <div className="finding-text">Ожидалось: {f.expected}</div>}
                    {f.found && (
                      <div className="finding-text text-muted">
                        Факт: <span>{f.found}</span>
                      </div>
                    )}
                    {f.recommendation && (
                      <div className="finding-text" style={{ marginTop: "var(--spacing-xs)" }}>
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
        </>
      )}
    </div>
  );
};
