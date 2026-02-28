import React, { useEffect, useState } from "react";
import { api, OrderItem, ProdamusPaymentItem } from "../api";

export const PaymentsPage: React.FC = () => {
  const [orders, setOrders] = useState<OrderItem[]>([]);
  const [payments, setPayments] = useState<ProdamusPaymentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const [ordersData, paymentsData] = await Promise.all([
          api.getOrders(),
          api.getPaymentsProdamus(),
        ]);
        setOrders(ordersData);
        setPayments(paymentsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка загрузки данных");
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const getStatusBadgeClass = (status: string): string => {
    if (status === "paid") return "badge badge-success";
    if (status === "failed" || status === "cancelled") return "badge badge-muted";
    return "badge";
  };

  const getPaymentForOrder = (orderId: number): ProdamusPaymentItem | undefined => {
    return payments.find((p) => p.order_id === orderId);
  };

  return (
    <div className="page-card">
      <div className="section-title-row">
        <div>
          <div className="page-title">Заказы и платежи (Prodamus)</div>
          <div className="page-description">
            Журнал заказов и платежей с отображением статуса, суммы, продукта и webhook-полей.
          </div>
        </div>
      </div>

      {loading ? (
        <div>Загрузка...</div>
      ) : error ? (
        <div style={{ color: "red" }}>Ошибка: {error}</div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Дата</th>
              <th>Пользователь</th>
              <th>Продукт</th>
              <th>Сумма</th>
              <th>Статус</th>
              <th>invoice_id</th>
            </tr>
          </thead>
          <tbody>
            {orders.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", color: "#999" }}>
                  Нет заказов
                </td>
              </tr>
            ) : (
              orders.map((order) => {
                const payment = getPaymentForOrder(order.id);
                return (
                  <tr key={order.id}>
                    <td>{new Date(order.created_at).toLocaleString("ru-RU")}</td>
                    <td>User #{order.user_id}</td>
                    <td>Product #{order.product_id}</td>
                    <td>
                      {order.amount} ₽
                    </td>
                    <td>
                      <span className={getStatusBadgeClass(order.status)}>{order.status}</span>
                    </td>
                    <td>{payment?.prodamus_invoice_id || "—"}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      )}
    </div>
  );
};




