import React from "react";

export const LogsPage: React.FC = () => {
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
          <tr>
            <td>12.02.2025 14:12</td>
            <td>admin@hse.ru</td>
            <td>Обновление шаблона v3</td>
            <td>template hse_journalism_2024_25</td>
          </tr>
          <tr>
            <td>12.02.2025 10:02</td>
            <td>system</td>
            <td>Ошибка воркера при проверке #3077</td>
            <td>worker</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};


