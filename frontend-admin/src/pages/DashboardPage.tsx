import React from "react";

export const DashboardPage: React.FC = () => {
  return (
    <div className="page-grid">
      <section className="page-card">
        <div className="page-title">Дашборд</div>
        <div className="page-description">
          Ключевые показатели: проверки, оплаты, среднее время обработки, ошибки воркера.
        </div>
        <div className="kpi-row">
          <div className="kpi-card">
            <div className="kpi-label">Проверок за сегодня</div>
            <div className="kpi-value">32</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Проверок за 7 дней</div>
            <div className="kpi-value">214</div>
          </div>
        </div>
        <div className="kpi-row" style={{ marginTop: 10 }}>
          <div className="kpi-card">
            <div className="kpi-label">Успешных оплат за сегодня</div>
            <div className="kpi-value">18</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Успешных оплат за 7 дней</div>
            <div className="kpi-value">96</div>
          </div>
        </div>
        <div className="kpi-row" style={{ marginTop: 10 }}>
          <div className="kpi-card">
            <div className="kpi-label">Среднее время обработки</div>
            <div className="kpi-value">38 с</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Ошибки воркера (последние)</div>
            <div className="kpi-value">0</div>
          </div>
        </div>
      </section>
      <section className="page-card">
        <div className="section-title-row">
          <div className="section-title">Последние события</div>
          <div className="section-caption">Оплаты и проверки в хронологии</div>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Время</th>
              <th>Событие</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>10:24</td>
              <td>Оплата #1042 (1 кредит)</td>
              <td>
                <span className="badge badge-success">paid</span>
              </td>
            </tr>
            <tr>
              <td>10:18</td>
              <td>Проверка #3081 — готово</td>
              <td>
                <span className="badge badge-success">done</span>
              </td>
            </tr>
            <tr>
              <td>10:02</td>
              <td>Проверка #3077 — ошибка воркера</td>
              <td>
                <span className="badge badge-muted">error</span>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  );
};



