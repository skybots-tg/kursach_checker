import React from "react";

export const TemplatesPage: React.FC = () => {
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
            <input className="field-input" placeholder="Фильтр по вузу или программе" />
          </div>
          <div>
            <div className="field-label">Тип работы</div>
            <select className="field-select">
              <option>Все</option>
              <option>Курсовая</option>
              <option>ВКР</option>
            </select>
          </div>
          <div>
            <div className="field-label">Статус</div>
            <select className="field-select">
              <option>Все</option>
              <option>Черновик</option>
              <option>Опубликован</option>
            </select>
          </div>
        </div>

        <table className="table">
          <thead>
            <tr>
              <th>Название</th>
              <th>ВУЗ / программа / тип работы</th>
              <th>Год</th>
              <th>Статус</th>
              <th>Версия</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>НИУ ВШЭ — Журналистика — Курсовая 2024/25</td>
              <td>НИУ ВШЭ / Журналистика / Курсовая</td>
              <td>2024/25</td>
              <td>
                <span className="badge badge-success">опубликован</span>
              </td>
              <td>v3</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section className="page-card">
        <div className="section-title-row">
          <div className="section-title">Версии и аудит</div>
          <div className="section-caption">История изменений выделенного шаблона</div>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Версия</th>
              <th>Статус</th>
              <th>Автор</th>
              <th>Дата</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>v3</td>
              <td>
                <span className="badge badge-success">опубликован</span>
              </td>
              <td>admin@hse.ru</td>
              <td>12.02.2025 14:12</td>
            </tr>
            <tr>
              <td>v2</td>
              <td>
                <span className="badge badge-muted">архив</span>
              </td>
              <td>methodist@hse.ru</td>
              <td>03.01.2025 11:08</td>
            </tr>
          </tbody>
        </table>
        <button className="secondary-btn" style={{ marginTop: 10 }}>
          Создать новую версию
        </button>
      </section>
    </div>
  );
};



