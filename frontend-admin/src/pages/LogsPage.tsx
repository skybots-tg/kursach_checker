import React, { useEffect, useState } from "react";
import { api, AuditLogItem } from "../api";

export const LogsPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadLogs = async () => {
      try {
        setLoading(true);
        const data = await api.getAuditLogs();
        setLogs(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка загрузки данных");
      } finally {
        setLoading(false);
      }
    };
    loadLogs();
  }, []);

  const formatEntity = (log: AuditLogItem): string => {
    if (log.entity_type && log.entity_id) {
      return `${log.entity_type} #${log.entity_id}`;
    }
    return "—";
  };

  return (
    <div className="page-card">
      <div className="section-title-row">
        <div>
          <div className="page-title">Логи и аудит</div>
          <div className="page-description">
            История действий админов, изменения шаблонов и ошибок воркера/вебхуков.
          </div>
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
              <th>Дата</th>
              <th>Админ</th>
              <th>Действие</th>
              <th>Объект</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr>
                <td colSpan={4} style={{ textAlign: "center", color: "#999" }}>
                  Нет логов
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id}>
                  <td>{new Date(log.created_at).toLocaleString("ru-RU")}</td>
                  <td>{log.admin_user_id ? `Admin #${log.admin_user_id}` : "system"}</td>
                  <td>{log.action}</td>
                  <td>{formatEntity(log)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}
    </div>
  );
};




