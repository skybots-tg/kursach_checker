import React from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { Icon } from "./components/Icon";
import { DashboardPage } from "./pages/DashboardPage";
import { UniversitiesPage } from "./pages/UniversitiesPage";
import { GostsPage } from "./pages/GostsPage";
import { TemplatesPage } from "./pages/TemplatesPage";
import { RulesLibraryPage } from "./pages/RulesLibraryPage";
import { AutoFixesPage } from "./pages/AutoFixesPage";
import { ProductsPage } from "./pages/ProductsPage";
import { PaymentsPage } from "./pages/PaymentsPage";
import { ChecksPage } from "./pages/ChecksPage";
import { UsersPage } from "./pages/UsersPage";
import { BotContentPage } from "./pages/BotContentPage";
import { DemoConfigPage } from "./pages/DemoConfigPage";
import { LogsPage } from "./pages/LogsPage";
import { SettingsPage } from "./pages/SettingsPage";

interface NavItem {
  to: string;
  icon: React.ComponentProps<typeof Icon>["name"];
  label: string;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", icon: "layout", label: "Дашборд" },
  { to: "/universities", icon: "university", label: "Вузы и программы" },
  { to: "/gosts", icon: "book", label: "ГОСТы и стили" },
  { to: "/templates", icon: "fileText", label: "Шаблоны проверок" },
  { to: "/rules", icon: "sliders", label: "Библиотека правил" },
  { to: "/autofixes", icon: "wand", label: "Автоисправления" },
  { to: "/products", icon: "creditCard", label: "Продукты и цены" },
  { to: "/payments", icon: "list", label: "Заказы и платежи" },
  { to: "/checks", icon: "list", label: "Проверки" },
  { to: "/users", icon: "users", label: "Пользователи" },
  { to: "/bot-content", icon: "messageSquare", label: "Контент бота" },
  { to: "/demo", icon: "fileText", label: "Демо-пример" },
  { to: "/logs", icon: "log", label: "Логи и аудит" },
  { to: "/settings", icon: "settings", label: "Настройки" }
];

export const App: React.FC = () => {
  return (
    <div className="admin-shell">
      <aside className="admin-sidebar glass-panel">
        <div className="sidebar-header">
          <div className="sidebar-logo">Kursach Admin</div>
          <div className="sidebar-subtitle">Техпроверка работ</div>
        </div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `sidebar-nav-item ${isActive ? "sidebar-nav-item-active" : ""}`
              }
            >
              <Icon name={item.icon} className="sidebar-nav-icon" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="admin-main">
        <header className="admin-topbar glass-panel">
          <div>
            <div className="topbar-title">Админка</div>
            <div className="topbar-subtitle">
              Управление вузами, шаблонами, проверками и оплатами
            </div>
          </div>
          <div className="topbar-user-badge">
            <span className="topbar-user-name">Admin</span>
            <span className="topbar-user-role">Суперадмин</span>
          </div>
        </header>
        <main className="admin-content">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/universities" element={<UniversitiesPage />} />
            <Route path="/gosts" element={<GostsPage />} />
            <Route path="/templates" element={<TemplatesPage />} />
            <Route path="/rules" element={<RulesLibraryPage />} />
            <Route path="/autofixes" element={<AutoFixesPage />} />
            <Route path="/products" element={<ProductsPage />} />
            <Route path="/payments" element={<PaymentsPage />} />
            <Route path="/checks" element={<ChecksPage />} />
            <Route path="/users" element={<UsersPage />} />
            <Route path="/bot-content" element={<BotContentPage />} />
            <Route path="/demo" element={<DemoConfigPage />} />
            <Route path="/logs" element={<LogsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
};




