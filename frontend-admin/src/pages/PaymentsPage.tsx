import React from "react";

export const PaymentsPage: React.FC = () => {
  return (
    <div className="page-card">
      <div className="section-title-row">
        <div>
          <div className="page-title">Заказы и платежи (Prodamus)</div>
          <div className="page-description">
            Журнал заказов и платежей с отображением статуса, суммы, продукта и webhook-полей.
          </div>
        </div>
      </div>

      <div className="field-row" style={{ marginBottom: 10 }}>
        <div style={{ flex: 1 }}>
          <div className="field-label">Поиск по пользователю или invoice_id</div>
          <input className="field-input" placeholder="telegram_id, email или invoice_id" />
        </div>
        <div>
          <div className="field-label">Статус</div>
          <select className="field-select">
            <option>Все</option>
            <option>created</option>
            <option>paid</option>
            <option>failed</option>
            <option>cancelled</option>
            <option>refund</option>
          </select>
        </div>
      </div>

      <table className="table">
        <thead>
          <tr>
            <th>Дата</th>
            <th>Пользователь</th>
            <th>Продукт</th>
            <th>Сумма</th>
            <th>Статус</th>
            <th>invoice_id</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>12.02.2025 10:24</td>
            <td>@student123</td>
            <td>1 проверка</td>
            <td>299 ₽</td>
            <td>
              <span className="badge badge-success">paid</span>
            </td>
            <td>inv_1042</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};


