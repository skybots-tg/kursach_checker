import React, { useEffect, useState } from "react";
import { Link, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { Icon } from "./components/Icon";
import { fetchMe, authWithTelegram, getToken } from "./api";
import type { MeResponse } from "./types";
import { HomePage } from "./pages/HomePage";
import { DemoPage } from "./pages/DemoPage";
import { CheckPage } from "./pages/CheckPage";
import { HistoryPage } from "./pages/HistoryPage";
import { ProfilePage } from "./pages/ProfilePage";
import { CheckResultPage } from "./pages/CheckResultPage";

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData?: string;
      };
    };
  }
}

function useMiniAppAuth(): { me: MeResponse | null; loading: boolean; error: string | null } {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      try {
        setLoading(true);
        setError(null);
        if (!getToken()) {
          const initData = window.Telegram?.WebApp?.initData || "";
          if (initData) {
            await authWithTelegram(initData);
          } else {
            setError("Не удалось получить initData Telegram. Откройте Mini App из бота.");
            setLoading(false);
            return;
          }
        }
        const profile = await fetchMe();
        if (!cancelled) {
          setMe(profile);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Auth error");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  return { me, loading, error };
}

function TopBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const [canGoBack, setCanGoBack] = useState(false);

  useEffect(() => {
    setCanGoBack(location.pathname.startsWith("/checks/"));
  }, [location.pathname]);

  let title = "Проверка работы";
  let subtitle: string | null = null;
  if (location.pathname === "/") {
    title = "Главная";
    subtitle = "Как это работает и демо";
  } else if (location.pathname.startsWith("/demo")) {
    title = "Демо-проверка";
    subtitle = "Пример отчёта до оплаты";
  } else if (location.pathname.startsWith("/check")) {
    title = "Новая проверка";
    subtitle = "Выбор шаблона и загрузка файла";
  } else if (location.pathname.startsWith("/history")) {
    title = "История";
    subtitle = "Проверки и оплаты";
  } else if (location.pathname.startsWith("/profile")) {
    title = "Профиль";
    subtitle = "Баланс и информация";
  } else if (location.pathname.startsWith("/checks/")) {
    title = "Результат проверки";
  }

  return (
    <header className="glass-card top-bar">
      {canGoBack && (
        <button className="top-bar-back" onClick={() => navigate(-1)} aria-label="Назад">
          <Icon name="chevron-left" className="bottom-nav-icon" />
        </button>
      )}
      <div>
        <div className="top-bar-title">{title}</div>
        {subtitle && <div className="top-bar-subtitle">{subtitle}</div>}
      </div>
      <div style={{ marginLeft: "auto", fontSize: 11, color: "#6b7280" }}>
        <Link to="/profile" style={{ textDecoration: "none", color: "inherit" }}>
          Mini App
        </Link>
      </div>
    </header>
  );
}

function BottomNav() {
  return (
    <nav className="glass-card bottom-nav">
      <NavLink to="/" end className={({ isActive }) => `bottom-nav-item ${isActive ? "bottom-nav-item-active" : ""}`}>
        <Icon name="home" className="bottom-nav-icon" />
        <span>Главная</span>
      </NavLink>
      <NavLink
        to="/check"
        className={({ isActive }) => `bottom-nav-item ${isActive ? "bottom-nav-item-active" : ""}`}
      >
        <Icon name="check" className="bottom-nav-icon" />
        <span>Проверка</span>
      </NavLink>
      <NavLink
        to="/history"
        className={({ isActive }) => `bottom-nav-item ${isActive ? "bottom-nav-item-active" : ""}`}
      >
        <Icon name="history" className="bottom-nav-icon" />
        <span>История</span>
      </NavLink>
      <NavLink
        to="/profile"
        className={({ isActive }) => `bottom-nav-item ${isActive ? "bottom-nav-item-active" : ""}`}
      >
        <Icon name="user" className="bottom-nav-icon" />
        <span>Профиль</span>
      </NavLink>
    </nav>
  );
}

export const App: React.FC = () => {
  const { me, loading, error } = useMiniAppAuth();

  return (
    <div className="app-shell">
      <TopBar />
      <main className="page-scroll">
        {loading && !me ? (
          <div className="glass-card" style={{ padding: 16, fontSize: 13 }}>
            Авторизация через Telegram…
          </div>
        ) : error && !me ? (
          <div className="glass-card" style={{ padding: 16, fontSize: 13 }}>
            <div className="page-section-title">Не удалось авторизоваться</div>
            <div className="page-section-description">{error}</div>
            <div style={{ fontSize: 12, marginTop: 8 }}>
              Откройте Mini App из Telegram‑бота, чтобы мы получили initData.
            </div>
          </div>
        ) : (
          <Routes>
            <Route path="/" element={<HomePage me={me!} />} />
            <Route path="/demo" element={<DemoPage />} />
            <Route path="/check" element={<CheckPage me={me!} />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/profile" element={<ProfilePage me={me!} />} />
            <Route path="/checks/:id" element={<CheckResultPage />} />
          </Routes>
        )}
      </main>
      <BottomNav />
    </div>
  );
};



