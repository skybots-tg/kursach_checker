import React from "react";
import type { MeResponse } from "../types";
import { Link } from "react-router-dom";

interface Props {
  me: MeResponse;
}

export const HomePage: React.FC<Props> = ({ me }) => {
  return (
    <div className="glass-card" style={{ padding: 16 }}>
      <div className="page-section-title">Как это работает</div>
      <div className="page-section-description">
        Загрузите курсовую или ВКР в формате DOCX — система проверит оформление по правилам вуза и ГОСТа и покажет
        подробный отчёт.
      </div>

      <div className="kpi-row">
        <div className="kpi-card">
          <div className="kpi-label">Доступно проверок</div>
          <div className="kpi-value">{me.credits_available}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Ваш Telegram</div>
          <div className="kpi-value" style={{ fontSize: 13 }}>
            {me.username || me.first_name || me.telegram_id}
          </div>
        </div>
      </div>

      <div className="spacer-16" />

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <Link to="/demo">
          <button className="secondary-btn" style={{ width: "100%" }}>
            Посмотреть демо‑отчёт
          </button>
        </Link>
        <Link to="/check">
          <button className="primary-btn" style={{ width: "100%" }}>
            Перейти к проверке
          </button>
        </Link>
      </div>

      <div className="spacer-16" />

      <div className="page-section-title">О нас</div>
      <div className="page-section-description">
        Сервис создан, чтобы студенты могли быстро проверить оформление работы по методичкам вуза и ГОСТам — без
        ручной вычитки десятков пунктов.
      </div>
    </div>
  );
};



