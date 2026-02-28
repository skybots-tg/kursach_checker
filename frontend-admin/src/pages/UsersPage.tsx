import React, { useEffect, useState } from "react";
import { api, UserItem } from "../api";

export const UsersPage: React.FC = () => {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    const loadUsers = async () => {
      try {
        setLoading(true);
        const data = await api.getUsers(search || undefined);
        setUsers(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка загрузки данных");
      } finally {
        setLoading(false);
      }
    };
    loadUsers();
  }, [search]);

  return (
    <div className="page-card">
      <div className="section-title-row">
        <div>
          <div className="page-title">Пользователи</div>
          <div className="page-description">
            Список пользователей Mini App и админов, баланс кредитов и последние активности.
          </div>
        </div>
      </div>

      <div className="field-row" style={{ marginBottom: 10 }}>
        <div style={{ flex: 1 }}>
          <div className="field-label">Поиск по telegram_id / username / email</div>
          <input
            className="field-input"
            placeholder="@username или id"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
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
              <th>Пользователь</th>
              <th>Telegram ID</th>
              <th>Баланс кредитов</th>
              <th>Создан</th>
              <th>Последний логин</th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: "center", color: "#999" }}>
                  Нет пользователей
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user.id}>
                  <td>
                    {user.username ? `@${user.username}` : user.first_name || `ID: ${user.telegram_id}`}
                  </td>
                  <td>{user.telegram_id}</td>
                  <td>{user.credits_balance}</td>
                  <td>{new Date(user.created_at).toLocaleDateString("ru-RU")}</td>
                  <td>
                    {user.last_login_at
                      ? new Date(user.last_login_at).toLocaleString("ru-RU")
                      : "—"}
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




