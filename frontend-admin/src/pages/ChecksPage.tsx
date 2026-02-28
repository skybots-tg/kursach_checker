import React, { useEffect, useState } from "react";
import { api, CheckItem } from "../api";

export const ChecksPage: React.FC = () => {
  const [checks, setChecks] = useState<CheckItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("Все");

  useEffect(() => {
    const loadChecks = async () => {
      try {
        setLoading(true);
        const data = await api.getChecks(search || undefined, statusFilter);
        setChecks(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка загрузки данных");
      } finally {
        setLoading(false);
      }
    };
    loadChecks();
  }, [search, statusFilter]);

  const formatDuration = (check: CheckItem): string => {
    if (!check.finished_at) return "—";
    const start = new Date(check.created_at).getTime();
    const end = new Date(check.finished_at).getTime();
    const seconds = Math.round((end - start) / 1000);
    return `${seconds} с`;
  };

  const getStatusBadgeClass = (status: string): string => {
    if (status === "done") return "badge badge-success";
    if (status === "error") return "badge badge-muted";
    return "badge";
  };

  return (
    <div className="page-card">
      <div className="section-title-row">
        <div>
          <div className="page-title">Проверки (журнал)</div>
          <div className="page-description">
            Список всех проверок: параметры запуска, длительность, счётчики ошибок/предупреждений и ссылки на файлы.
          </div>
        </div>
      </div>

      <div className="field-row" style={{ marginBottom: 10 }}>
        <div style={{ flex: 1 }}>
          <div className="field-label">Поиск по пользователю или ID проверки</div>
          <input
            className="field-input"
            placeholder="telegram_id или id проверки"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div>
          <div className="field-label">Статус</div>
          <select
            className="field-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option>Все</option>
            <option>queued</option>
            <option>running</option>
            <option>done</option>
            <option>error</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div>Загрузка...</div>
      ) : error ? (
        <div style={{ color: "red" }}>Ошибка: {error}</div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Пользователь</th>
              <th>Шаблон / ГОСТ</th>
              <th>Статус</th>
              <th>Длительность</th>
              <th>Создано</th>
            </tr>
          </thead>
          <tbody>
            {checks.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", color: "#999" }}>
                  Нет проверок
                </td>
              </tr>
            ) : (
              checks.map((check) => (
                <tr key={check.id}>
                  <td>#{check.id}</td>
                  <td>{check.user_id}</td>
                  <td>Template #{check.template_version_id}</td>
                  <td>
                    <span className={getStatusBadgeClass(check.status)}>{check.status}</span>
                  </td>
                  <td>{formatDuration(check)}</td>
                  <td>{new Date(check.created_at).toLocaleString("ru-RU")}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}
    </div>
  );
};




