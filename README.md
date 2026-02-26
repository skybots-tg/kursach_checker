## Система проверки оформления документов (курсовые/ВКР)

Проект реализует backend (FastAPI + asyncio + SQLAlchemy async + PostgreSQL + Redis), Telegram‑бот (aiogram 3), Telegram Mini App для студентов и веб‑админку для методистов/администраторов.

Основные директории:

- `backend` — FastAPI, бизнес‑логика, rules engine, очередь задач.
- `bot` — Telegram‑бот на aiogram.
- `frontend-miniapp` — клиентский веб‑интерфейс (Telegram Mini App).
- `frontend-admin` — веб‑админка.
- `rules_specs` — человеко‑читаемые и машинные описания универсальных шаблонов/ГОСТов.

Backend запускается на порту `8343` (см. `backend/main.py`).

### Основные HTTP‑контуры (соответствие tech_spec.md)

- **Mini App (`/api/miniapp`)**:
  - `POST /auth/telegram` — авторизация по initData.
  - `GET /me` — профиль и баланс кредитов.
  - `GET /universities`, `GET /gosts`, `GET /templates` — справочники.
  - `GET /products` — активные продукты/тарифы.
  - `POST /payments/create` — создание заказа и ссылки оплаты (Prodamus).
  - `POST /payments/webhook/prodamus` — webhook с идемпотентным начислением кредитов.
  - `POST /files/upload` — загрузка DOC/DOCX для проверки.
  - `POST /checks/start` — запуск проверки (списание кредита + постановка в очередь).
  - `GET /checks`, `GET /checks/{id}` — история и детали проверок (отчёт `CheckReport`).
  - `GET /files/{id}/download` — скачивание входного/выходного файла и отчёта.
  - `GET /demo/check` — предзагруженный демо‑отчёт для экрана «Демо».

- **Admin (`/api/admin`)**:
  - `GET /health` — healthcheck.
  - CRUD вузов: `GET/POST/PUT /universities`.
  - CRUD ГОСТов: `GET/POST/PUT /gosts`.
  - CRUD шаблонов: `GET/POST/PUT /templates`.
  - Версии шаблонов: `GET/POST /templates/{id}/versions`, `GET/PUT /template_versions/{id}` (rules_json как `TemplateRulesConfig`).
  - Контент бота: `GET/POST/PUT/DELETE /bot_content` + `GET /audit_logs` (минимальный аудит изменений).
  - Продукты и цены: `GET/POST/PUT /products`.
  - Журнал заказов и платежей: `GET /orders`, `GET /payments_prodamus`.
  - Журнал проверок: `GET /checks`.
