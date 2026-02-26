import React from "react";

export const UniversitiesPage: React.FC = () => {
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
          <input className="field-input" placeholder="Начните вводить название вуза…" />
        </div>
        <div>
          <div className="field-label">Статус</div>
          <select className="field-select">
            <option>Все</option>
            <option>Активен</option>
            <option>Архив</option>
          </select>
        </div>
      </div>

      <table className="table">
        <thead>
          <tr>
            <th>ВУЗ</th>
            <th>Программа</th>
            <th>Типы работ</th>
            <th>Привязанные шаблоны</th>
            <th>Статус</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>НИУ ВШЭ</td>
            <td>Журналистика</td>
            <td>Курсовая, ВКР</td>
            <td>3 шаблона</td>
            <td>
              <span className="badge badge-success">активен</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};



