import React, { useEffect, useState } from "react";
import { api, ProductItem } from "../api";

export const ProductsPage: React.FC = () => {
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadProducts = async () => {
      try {
        setLoading(true);
        const data = await api.getProducts();
        setProducts(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка загрузки данных");
      } finally {
        setLoading(false);
      }
    };
    loadProducts();
  }, []);

  return (
    <div className="page-card">
      <div className="section-title-row">
        <div>
          <div className="page-title">Продукты и цены</div>
          <div className="page-description">
            Настройка кредитов за проверки, пакетов и описаний для Mini App.
          </div>
        </div>
        <button className="primary-btn">Добавить продукт</button>
      </div>

      {loading ? (
        <div>Загрузка...</div>
      ) : error ? (
        <div style={{ color: "red" }}>Ошибка: {error}</div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Название</th>
              <th>Цена</th>
              <th>Кредитов</th>
              <th>Описание</th>
              <th>Активность</th>
            </tr>
          </thead>
          <tbody>
            {products.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: "center", color: "#999" }}>
                  Нет продуктов
                </td>
              </tr>
            ) : (
              products.map((product) => (
                <tr key={product.id}>
                  <td>{product.name}</td>
                  <td>
                    {product.price} {product.currency}
                  </td>
                  <td>{product.credits_amount}</td>
                  <td>{product.description || "—"}</td>
                  <td>
                    <span className={`badge ${product.active ? "badge-success" : "badge-muted"}`}>
                      {product.active ? "активен" : "неактивен"}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}
    </div>
  );
};




