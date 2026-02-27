import React from "react";

export const UsersPage: React.FC = () => {
  return (
    <div className="page-card">
      <div className="section-title-row">
        <div>
          <div className="page-title">Пользователи</div>
          <div className="page-description">
            Список пользователей Mini App и админов, баланс кредитов и последние активности.
          </div>
        </div>
      </div>

      <div className="field-row" style={{ marginBottom: 10 }}>
        <div style={{ flex: 1 }}>
          <div className="field-label">Поиск по telegram_id / username / email</div>
          <input className="field-input" placeholder="@username или id" />
        </div>
      </div>

      <table className="table">
        <thead>
          <tr>
            <th>Пользователь</th>
            <th>Telegram ID</th>
            <th>Баланс кредитов</th>
            <th>Создан</th>
            <th>Последний логин</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>@student123</td>
            <td>123456789</td>
            <td>2</td>
            <td>01.02.2025</td>
            <td>12.02.2025 10:20</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};




