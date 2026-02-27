import React from "react";

export const ProductsPage: React.FC = () => {
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
          <tr>
            <td>1 проверка</td>
            <td>299 ₽</td>
            <td>1</td>
            <td>Одна техническая проверка документа</td>
            <td>
              <span className="badge badge-success">активен</span>
            </td>
          </tr>
          <tr>
            <td>5 проверок</td>
            <td>1190 ₽</td>
            <td>5</td>
            <td>Пакет для нескольких работ или перепроверок</td>
            <td>
              <span className="badge badge-success">активен</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};




