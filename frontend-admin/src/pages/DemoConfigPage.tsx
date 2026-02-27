import React from "react";

export const DemoConfigPage: React.FC = () => {
  return (
    <div className="page-grid">
      <section className="page-card">
        <div className="section-title-row">
          <div>
            <div className="page-title">Демо-пример</div>
            <div className="page-description">
              Управление примером документа и отчёта, который показывается в Mini App до оплаты.
            </div>
          </div>
        </div>

        <div className="field-row" style={{ marginBottom: 8 }}>
          <div style={{ flex: 1 }}>
            <div className="field-label">Пример документа</div>
            <input type="file" className="field-input" />
          </div>
        </div>
        <div className="field-row" style={{ marginBottom: 8 }}>
          <div style={{ flex: 1 }}>
            <div className="field-label">Пример отчёта (JSON)</div>
            <input type="file" className="field-input" />
          </div>
        </div>

        <button className="primary-btn">Сохранить демо-настройки</button>
      </section>

      <section className="page-card">
        <div className="section-title-row">
          <div className="section-title">Предпросмотр демо</div>
          <div className="section-caption">Как студент увидит демо-отчёт</div>
        </div>
        <p style={{ fontSize: 13, color: "var(--text-muted)" }}>
          Здесь можно отобразить врезку с основными показателями демо-отчёта и пример карточек ошибок/предупреждений
          так же, как в Mini App.
        </p>
      </section>
    </div>
  );
};




