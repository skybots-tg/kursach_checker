import React from "react";

export const SettingsPage: React.FC = () => {
  return (
    <div className="page-card">
      <div className="section-title-row">
        <div>
          <div className="page-title">Настройки</div>
          <div className="page-description">
            Общие параметры системы: интеграции, роли админов, ограничения и технические опции.
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 520 }}>
        <div className="field-row" style={{ marginBottom: 8 }}>
          <div style={{ flex: 1 }}>
            <div className="field-label">Prodamus webhook URL</div>
            <input className="field-input" defaultValue="https://api.example.com/api/payments/webhook/prodamus" />
          </div>
        </div>
        <div className="field-row" style={{ marginBottom: 8 }}>
          <div style={{ flex: 1 }}>
            <div className="field-label">Redis rate limit (запросов в минуту)</div>
            <input className="field-input" defaultValue="60" />
          </div>
        </div>
        <button className="primary-btn">Сохранить настройки</button>
      </div>
    </div>
  );
};



