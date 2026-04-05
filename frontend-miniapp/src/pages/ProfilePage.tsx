import React, { useEffect, useState } from "react";
import type { MeResponse, ProductItem } from "../types";
import { createPayment, fetchProducts } from "../api";
import { Icon } from "../components/Icon";
import { pluralize } from "../pluralize";

interface Props {
  me: MeResponse;
}

export const ProfilePage: React.FC<Props> = ({ me }) => {
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creatingOrderId, setCreatingOrderId] = useState<number | null>(null);
  const [paymentUrl, setPaymentUrl] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        const ps = await fetchProducts();
        if (!cancelled) setProducts(ps);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Ошибка загрузки продуктов");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleBuy(productId: number) {
    const tg = (window as any).Telegram?.WebApp;

    // Открываем пустое окно синхронно, пока ещё жив user-gesture контекст.
    // На Telegram Web openLink внутри делает window.open — после await
    // браузер заблокирует его как popup.
    let popupWindow: Window | null = null;
    if (!tg?.openLink) {
      popupWindow = window.open("about:blank", "_blank");
    }

    try {
      setCreatingOrderId(productId);
      setPaymentUrl(null);
      setError(null);
      const res = await createPayment(productId);

      let opened = false;

      if (tg?.openLink) {
        try {
          tg.openLink(res.payment_url, { try_instant_view: false });
          opened = true;
        } catch { /* fallback ниже */ }
      }

      if (!opened && popupWindow && !popupWindow.closed) {
        popupWindow.location.href = res.payment_url;
        opened = true;
      }

      // Всегда показываем ссылку как fallback — если openLink/popup
      // не сработал, пользователь сможет перейти вручную
      setPaymentUrl(res.payment_url);
    } catch (e) {
      popupWindow?.close();
      setError(e instanceof Error ? e.message : "Не удалось создать оплату");
    } finally {
      setCreatingOrderId(null);
    }
  }

  return (
    <div className="glass-card" style={{ padding: "var(--spacing-lg)" }}>
      <div className="page-section-title">Профиль</div>
      <div className="page-section-description">
        {me.first_name && (
          <>
            {me.first_name}
            {me.username ? ` (@${me.username})` : ""}
          </>
        )}
      </div>

      <div className="spacer-8" />

      <div className="field-label">Баланс</div>
      <div className="credits-badge">
        Проверок доступно: <strong>{me.credits_available}</strong>
      </div>

      <div className="spacer-16" />

      <div className="page-section-title">Пополнить баланс</div>
      {loading ? (
        <div style={{ fontSize: "var(--font-size-sm)" }}>Загружаем тарифы…</div>
      ) : error ? (
        <div style={{ fontSize: "var(--font-size-sm)", color: "var(--accent-error)" }}>{error}</div>
      ) : (
        <div className="card-list">
          {products.map((p) => (
            <div key={p.id} className="finding-card">
              <div className="finding-title-row">
                <div className="finding-title">{p.name}</div>
                <div style={{ fontSize: "var(--font-size-sm)", fontWeight: 600, color: "var(--accent-primary)" }}>
                  {p.price} {p.currency}
                </div>
              </div>
              <div className="finding-meta">
                {pluralize(p.credits_amount, "проверка", "проверки", "проверок")} · {p.description || "Пакет проверок"}
              </div>
              <div className="spacer-8" />
              <button
                className="primary-btn"
                style={{ width: "100%" }}
                onClick={() => handleBuy(p.id)}
                disabled={creatingOrderId === p.id}
              >
                <Icon name="credit-card" className="bottom-nav-icon" />{" "}
                {creatingOrderId === p.id ? "Переходим к оплате…" : "Оплатить"}
              </button>
            </div>
          ))}
          {products.length === 0 && (
            <div className="page-section-description">Тарифы пока не настроены. Попробуйте позже.</div>
          )}
        </div>
      )}

      {paymentUrl && (
        <>
          <div className="spacer-16" />
          <div className="finding-card" style={{ borderColor: "var(--accent-primary)" }}>
            <div className="finding-title">Ссылка на оплату готова</div>
            <div className="spacer-8" />
            <a
              href={paymentUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="primary-btn"
              style={{ width: "100%", display: "block", textAlign: "center", textDecoration: "none" }}
            >
              Перейти к оплате
            </a>
            <div className="spacer-8" />
            <div className="finding-meta">
              Если переход не произошёл автоматически, нажмите кнопку выше.
            </div>
          </div>
        </>
      )}

      <div className="spacer-16" />

      <div className="page-section-title">Поддержка</div>
      <div className="page-section-description">
        Если что-то пошло не так с оплатой или проверкой, напишите в поддержку — контакты доступны через Telegram‑бота.
      </div>
    </div>
  );
};




