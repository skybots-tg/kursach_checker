import React, { useEffect, useState } from "react";
import { api, UniversityItem } from "../api";

export const UniversitiesPage: React.FC = () => {
  const [universities, setUniversities] = useState<UniversityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("Все");

  useEffect(() => {
    const loadUniversities = async () => {
      try {
        setLoading(true);
        const data = await api.getUniversities();
        let filtered = data;
        
        if (search) {
          filtered = filtered.filter((u) =>
            u.name.toLowerCase().includes(search.toLowerCase())
          );
        }
        
        if (statusFilter !== "Все") {
          const isActive = statusFilter === "Активен";
          filtered = filtered.filter((u) => u.active === isActive);
        }
        
        setUniversities(filtered);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка загрузки данных");
      } finally {
        setLoading(false);
      }
    };
    loadUniversities();
  }, [search, statusFilter]);

  return (
    <div className="page-card">
      <div className="section-title-row">
        <div>
          <div className="page-title">ВУЗы и программы</div>
          <div className="page-description">
            Справочник вузов, подразделений, программ и типов работ. Поиск, фильтры, привязка шаблонов.
          </div>
        </div>
        <button className="primary-btn">Добавить вуз</button>
      </div>

      <div className="field-row" style={{ marginBottom: 10 }}>
        <div style={{ flex: 1 }}>
          <div className="field-label">Поиск по названию</div>
          <input
            className="field-input"
            placeholder="Начните вводить название вуза…"
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
            <option>Активен</option>
            <option>Архив</option>
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
              <th>ВУЗ</th>
              <th>Описание</th>
              <th>Приоритет</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
            {universities.length === 0 ? (
              <tr>
                <td colSpan={4} style={{ textAlign: "center", color: "#999" }}>
                  Нет вузов
                </td>
              </tr>
            ) : (
              universities.map((uni) => (
                <tr key={uni.id}>
                  <td>{uni.name}</td>
                  <td>{uni.description || "—"}</td>
                  <td>{uni.priority}</td>
                  <td>
                    <span className={`badge ${uni.active ? "badge-success" : "badge-muted"}`}>
                      {uni.active ? "активен" : "архив"}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}
    </div>
  );
};




