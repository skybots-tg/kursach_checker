import React, { useEffect, useState } from "react";
import { api, GostItem } from "../api";

export const GostsPage: React.FC = () => {
  const [gosts, setGosts] = useState<GostItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("Все");

  useEffect(() => {
    const loadGosts = async () => {
      try {
        setLoading(true);
        const data = await api.getGosts();
        let filtered = data;
        
        if (search) {
          filtered = filtered.filter((g) =>
            g.name.toLowerCase().includes(search.toLowerCase())
          );
        }
        
        if (typeFilter !== "Все") {
          filtered = filtered.filter((g) => g.type === typeFilter);
        }
        
        setGosts(filtered);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка загрузки данных");
      } finally {
        setLoading(false);
      }
    };
    loadGosts();
  }, [search, typeFilter]);

  return (
    <div className="page-card">
      <div className="section-title-row">
        <div>
          <div className="page-title">ГОСТы и стили оформления</div>
          <div className="page-description">
            Конфигурация стандартов оформления: структура, ссылки, литература, комбинированные профили.
          </div>
        </div>
        <button className="primary-btn">Добавить ГОСТ</button>
      </div>

      <div className="field-row" style={{ marginBottom: 10 }}>
        <div style={{ flex: 1 }}>
          <div className="field-label">Поиск по названию</div>
          <input
            className="field-input"
            placeholder="Например, ГОСТ 7.0.5-2008"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div>
          <div className="field-label">Тип</div>
          <select
            className="field-select"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            <option>Все</option>
            <option>Структура</option>
            <option>Ссылки</option>
            <option>Литература</option>
            <option>Комбинированный</option>
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
              <th>Тип</th>
              <th>Версия / год</th>
              <th>Описание для клиента</th>
              <th>Активность</th>
            </tr>
          </thead>
          <tbody>
            {gosts.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: "center", color: "#999" }}>
                  Нет ГОСТов
                </td>
              </tr>
            ) : (
              gosts.map((gost) => (
                <tr key={gost.id}>
                  <td>{gost.name}</td>
                  <td>{gost.type || "—"}</td>
                  <td>{gost.year || "—"}</td>
                  <td>{gost.description || "—"}</td>
                  <td>
                    <span className={`badge ${gost.active ? "badge-success" : "badge-muted"}`}>
                      {gost.active ? "активен" : "неактивен"}
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




