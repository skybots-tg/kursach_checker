import React from "react";

export const GostsPage: React.FC = () => {
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
          <input className="field-input" placeholder="Например, ГОСТ 7.0.5-2008" />
        </div>
        <div>
          <div className="field-label">Тип</div>
          <select className="field-select">
            <option>Все</option>
            <option>Структура</option>
            <option>Ссылки</option>
            <option>Литература</option>
            <option>Комбинированный</option>
          </select>
        </div>
      </div>

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
          <tr>
            <td>ГОСТ 7.0.5-2008</td>
            <td>Ссылки и литература</td>
            <td>2008</td>
            <td>Оформление библиографии и ссылок</td>
            <td>
              <span className="badge badge-success">активен</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};



