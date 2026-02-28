import React, { useEffect, useState } from "react";
import { api, TemplateItem } from "../api";

export const TemplatesPage: React.FC = () => {
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("Все");
  const [statusFilter, setStatusFilter] = useState("Все");

  useEffect(() => {
    const loadTemplates = async () => {
      try {
        setLoading(true);
        const data = await api.getTemplates();
        let filtered = data;
        
        if (search) {
          filtered = filtered.filter((t) =>
            t.name.toLowerCase().includes(search.toLowerCase())
          );
        }
        
        if (typeFilter !== "Все") {
          filtered = filtered.filter((t) => t.type_work === typeFilter);
        }
        
        if (statusFilter !== "Все") {
          const statusMap: Record<string, string> = {
            "Черновик": "draft",
            "Опубликован": "published",
          };
          const targetStatus = statusMap[statusFilter];
          if (targetStatus) {
            filtered = filtered.filter((t) => t.status === targetStatus);
          }
        }
        
        setTemplates(filtered);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка загрузки данных");
      } finally {
        setLoading(false);
      }
    };
    loadTemplates();
  }, [search, typeFilter, statusFilter]);

  const getStatusBadgeClass = (status: string): string => {
    if (status === "published") return "badge badge-success";
    return "badge badge-muted";
  };

  const formatStatus = (status: string): string => {
    const statusMap: Record<string, string> = {
      draft: "черновик",
      published: "опубликован",
    };
    return statusMap[status] || status;
  };

  return (
    <div className="page-grid">
      <section className="page-card">
        <div className="section-title-row">
          <div>
            <div className="page-title">Шаблоны проверок</div>
            <div className="page-description">
              Профили вузов/программ/типов работ. Версионирование и статус публикации.
            </div>
          </div>
          <button className="primary-btn">Создать шаблон</button>
        </div>

        <div className="field-row" style={{ marginBottom: 10 }}>
          <div style={{ flex: 1 }}>
            <div className="field-label">ВУЗ / программа</div>
            <input
              className="field-input"
              placeholder="Фильтр по вузу или программе"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div>
            <div className="field-label">Тип работы</div>
            <select
              className="field-select"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <option>Все</option>
              <option>Курсовая</option>
              <option>ВКР</option>
            </select>
          </div>
          <div>
            <div className="field-label">Статус</div>
            <select
              className="field-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option>Все</option>
              <option>Черновик</option>
              <option>Опубликован</option>
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
                <th>Название</th>
                <th>ВУЗ ID</th>
                <th>Тип работы</th>
                <th>Год</th>
                <th>Статус</th>
              </tr>
            </thead>
            <tbody>
              {templates.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: "center", color: "#999" }}>
                    Нет шаблонов
                  </td>
                </tr>
              ) : (
                templates.map((template) => (
                  <tr key={template.id}>
                    <td>{template.name}</td>
                    <td>University #{template.university_id}</td>
                    <td>{template.type_work}</td>
                    <td>{template.year || "—"}</td>
                    <td>
                      <span className={getStatusBadgeClass(template.status)}>
                        {formatStatus(template.status)}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </section>

      <section className="page-card">
        <div className="section-title-row">
          <div className="section-title">Версии и аудит</div>
          <div className="section-caption">История изменений выделенного шаблона</div>
        </div>
        <div style={{ color: "#999", textAlign: "center", padding: "20px" }}>
          Выберите шаблон для просмотра версий
        </div>
      </section>
    </div>
  );
};




