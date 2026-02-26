import React from "react";

export const AutoFixesPage: React.FC = () => {
  return (
    <div className="page-card">
      <div className="section-title-row">
        <div>
          <div className="page-title">Автоисправления</div>
          <div className="page-description">
            Настройка типов правил, поддерживающих безопасные автоисправления, и дефолтных значений для шаблонов.
          </div>
        </div>
      </div>

      <table className="table">
        <thead>
          <tr>
            <th>Правило</th>
            <th>Описание</th>
            <th>Безопасность</th>
            <th>По умолчанию</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Выравнивание абзацев</td>
            <td>Приведение выравнивания основного текста к &quot;по ширине&quot;</td>
            <td>Безопасно</td>
            <td>
              <span className="badge badge-success">включено</span>
            </td>
          </tr>
          <tr>
            <td>Межстрочный интервал</td>
            <td>Фиксация интервала для основного текста (например, 1.5)</td>
            <td>Безопасно</td>
            <td>
              <span className="badge badge-success">включено</span>
            </td>
          </tr>
          <tr>
            <td>Структура разделов</td>
            <td>Автодобавление/перемещение разделов</td>
            <td>Небезопасно (только рекомендации)</td>
            <td>
              <span className="badge badge-muted">выключено</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};


