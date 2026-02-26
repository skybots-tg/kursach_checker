import React from "react";

export const RulesLibraryPage: React.FC = () => {
  return (
    <div className="page-grid">
      <section className="page-card">
        <div className="section-title-row">
          <div>
            <div className="page-title">Библиотека правил</div>
            <div className="page-description">
              Универсальный каталог правил (поля, шрифт, структура, объём, источники и т.п.) для сборки шаблонов.
            </div>
          </div>
          <button className="primary-btn">Добавить правило</button>
        </div>

        <div className="field-row" style={{ marginBottom: 10 }}>
          <div style={{ flex: 1 }}>
            <div className="field-label">Поиск по названию правила</div>
            <input className="field-input" placeholder="Например, Основной текст — шрифт и интервал" />
          </div>
          <div>
            <div className="field-label">Категория</div>
            <select className="field-select">
              <option>Все</option>
              <option>Файл</option>
              <option>Страница и поля</option>
              <option>Основной текст</option>
              <option>Структура</option>
              <option>Источники</option>
              <option>Объём</option>
            </select>
          </div>
        </div>

        <table className="table">
          <thead>
            <tr>
              <th>Название</th>
              <th>Категория</th>
              <th>Строгость по умолчанию</th>
              <th>Автоисправление</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Файл — режим правок и комментарии</td>
              <td>Техническая чистота</td>
              <td>Ошибка</td>
              <td>нет</td>
            </tr>
            <tr>
              <td>Основной текст — шрифт, кегль, интервал</td>
              <td>Основной текст</td>
              <td>Ошибка</td>
              <td>поддерживается</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section className="page-card">
        <div className="section-title-row">
          <div className="section-title">Группы и теги</div>
          <div className="section-caption">Организация правил по блокам конструктора</div>
        </div>
        <div className="chips-row">
          <span className="chip">Приём файла</span>
          <span className="chip">Техническая чистота</span>
          <span className="chip">Страница и поля</span>
          <span className="chip">Основной текст</span>
          <span className="chip">Источники и список литературы</span>
          <span className="chip">Объём</span>
        </div>
      </section>
    </div>
  );
};



