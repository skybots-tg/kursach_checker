import React, { useEffect, useState } from "react";
import type { MeResponse, ProductItem } from "../types";
import { createPayment, fetchProducts } from "../api";
import { Icon } from "../components/Icon";

interface Props {
  me: MeResponse;
}

export const ProfilePage: React.FC<Props> = ({ me }) => {
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creatingOrderId, setCreatingOrderId] = useState<number | null>(null);

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
    try {
      setCreatingOrderId(productId);
      const res = await createPayment(productId);
      window.open(res.payment_url, "_blank");
    } catch (e) {
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
                Кредитов: {p.credits_amount} · {p.description || "Пакет проверок"}
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

      <div className="spacer-16" />

      <div className="page-section-title">Поддержка</div>
      <div className="page-section-description">
        Если что-то пошло не так с оплатой или проверкой, напишите в поддержку — контакты доступны через Telegram‑бота.
      </div>
    </div>
  );
};




