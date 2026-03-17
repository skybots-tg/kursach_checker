import React from "react";
import type { MeResponse } from "../types";
import { Link } from "react-router-dom";
import { Icon } from "../components/Icon";

interface Props {
  me: MeResponse;
}

export const HomePage: React.FC<Props> = ({ me }) => {
  return (
    <div className="home-container">
      {/* Hero section */}
      <div className="home-hero">
        <div className="home-hero-icon">
          <Icon name="file-search" style={{ width: 32, height: 32 }} />
        </div>
        <h1 className="home-hero-title">Проверка оформления</h1>
        <p className="home-hero-subtitle">
          Загрузите DOCX — получите подробный отчёт по ГОСТу и методичке вуза за секунды
        </p>
      </div>

      {/* Stats row */}
      <div className="home-stats">
        <div className="home-stat-card home-stat-accent">
          <Icon name="zap" className="home-stat-icon" />
          <div className="home-stat-value">{me.credits_available}</div>
          <div className="home-stat-label">Доступно проверок</div>
        </div>
        <div className="home-stat-card">
          <Icon name="user" className="home-stat-icon" />
          <div className="home-stat-value home-stat-value-sm">
            {me.username || me.first_name || `ID ${me.telegram_id}`}
          </div>
          <div className="home-stat-label">Telegram</div>
        </div>
      </div>

      {/* Steps */}
      <div className="home-section-label">Как это работает</div>
      <div className="home-steps">
        <div className="home-step">
          <div className="home-step-num">1</div>
          <div className="home-step-body">
            <div className="home-step-title">Загрузите файл</div>
            <div className="home-step-desc">Курсовая или ВКР в формате DOCX</div>
          </div>
        </div>
        <div className="home-step">
          <div className="home-step-num">2</div>
          <div className="home-step-body">
            <div className="home-step-title">Автопроверка</div>
            <div className="home-step-desc">Система проверяет оформление по правилам</div>
          </div>
        </div>
        <div className="home-step">
          <div className="home-step-num">3</div>
          <div className="home-step-body">
            <div className="home-step-title">Получите отчёт</div>
            <div className="home-step-desc">Подробный список замечаний с рекомендациями</div>
          </div>
        </div>
      </div>

      {/* CTA buttons */}
      <div className="home-actions">
        <Link to="/check" style={{ textDecoration: "none", width: "100%" }}>
          <button className="primary-btn home-cta-primary">
            <Icon name="sparkles" style={{ width: 18, height: 18 }} />
            Начать проверку
            <Icon name="arrow-right" style={{ width: 16, height: 16, opacity: 0.7 }} />
          </button>
        </Link>
        <Link to="/demo" style={{ textDecoration: "none", width: "100%" }}>
          <button className="secondary-btn home-cta-secondary">
            <Icon name="play" style={{ width: 16, height: 16 }} />
            Посмотреть демо-отчёт
          </button>
        </Link>
      </div>

      {/* Features */}
      <div className="home-section-label">Преимущества</div>
      <div className="home-features">
        <div className="home-feature">
          <div className="home-feature-icon home-feature-icon--blue">
            <Icon name="shield-check" style={{ width: 20, height: 20 }} />
          </div>
          <div>
            <div className="home-feature-title">По ГОСТу</div>
            <div className="home-feature-desc">Проверка по актуальным стандартам</div>
          </div>
        </div>
        <div className="home-feature">
          <div className="home-feature-icon home-feature-icon--green">
            <Icon name="zap" style={{ width: 20, height: 20 }} />
          </div>
          <div>
            <div className="home-feature-title">Быстро</div>
            <div className="home-feature-desc">Результат за несколько секунд</div>
          </div>
        </div>
        <div className="home-feature">
          <div className="home-feature-icon home-feature-icon--purple">
            <Icon name="graduation-cap" style={{ width: 20, height: 20 }} />
          </div>
          <div>
            <div className="home-feature-title">По методичке</div>
            <div className="home-feature-desc">Правила именно вашего вуза</div>
          </div>
        </div>
      </div>
    </div>
  );
};
