import React from "react";

export const BotContentPage: React.FC = () => {
  return (
    <div className="page-grid">
      <section className="page-card">
        <div className="section-title-row">
          <div>
            <div className="page-title">Контент бота и меню</div>
            <div className="page-description">
              Тексты приветствий, FAQ, сообщений об оплате и готовности, а также структура inline-меню.
            </div>
          </div>
        </div>

        <div className="field-row" style={{ marginBottom: 8 }}>
          <div style={{ flex: 1 }}>
            <div className="field-label">Приветственное сообщение</div>
            <textarea className="field-input" rows={3} defaultValue="Привет! Я помогу проверить оформление вашей работы." />
          </div>
        </div>
        <div className="field-row" style={{ marginBottom: 8 }}>
          <div style={{ flex: 1 }}>
            <div className="field-label">Сообщение об успешной оплате</div>
            <textarea className="field-input" rows={3} defaultValue="Оплата получена, кредиты начислены. Можно запускать проверку." />
          </div>
        </div>
        <button className="primary-btn">Сохранить тексты</button>
      </section>

      <section className="page-card">
        <div className="section-title-row">
          <div className="section-title">Меню бота</div>
          <div className="section-caption">Структура inline‑кнопок</div>
        </div>
        <ul style={{ listStyle: "none", padding: 0, margin: 0, fontSize: 13 }}>
          <li>▶ Проверить документ → Mini App (вкладка Проверка)</li>
          <li>▶ Мои проверки → Mini App (вкладка История)</li>
          <li>▶ О нас / Отзывы / FAQ → страницы из админки</li>
          <li>▶ Поддержка → контакт/ссылка</li>
        </ul>
      </section>
    </div>
  );
};



