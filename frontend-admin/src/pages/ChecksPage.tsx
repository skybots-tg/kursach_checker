import React from "react";

export const ChecksPage: React.FC = () => {
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
          <input className="field-input" placeholder="telegram_id или id проверки" />
        </div>
        <div>
          <div className="field-label">Статус</div>
          <select className="field-select">
            <option>Все</option>
            <option>queued</option>
            <option>running</option>
            <option>done</option>
            <option>error</option>
          </select>
        </div>
      </div>

      <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Пользователь</th>
            <th>Шаблон / ГОСТ</th>
            <th>Статус</th>
            <th>Длительность</th>
            <th>Ошибки / предупреждения</th>
            <th>Файлы</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>#3081</td>
            <td>@student123</td>
            <td>НИУ ВШЭ — Журфак / ГОСТ 7.0.5</td>
            <td>
              <span className="badge badge-success">done</span>
            </td>
            <td>32 с</td>
            <td>5 / 8</td>
            <td>Входной / Отчёт / Исправленный</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};


