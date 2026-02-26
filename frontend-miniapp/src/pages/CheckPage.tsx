import React, { useEffect, useState } from "react";
import type { GostItem, MeResponse, TemplateItem, UniversityItem } from "../types";
import { fetchGosts, fetchTemplates, fetchUniversities, uploadFile, startCheck } from "../api";
import { Icon } from "../components/Icon";
import { useNavigate } from "react-router-dom";

interface Props {
  me: MeResponse;
}

export const CheckPage: React.FC<Props> = ({ me }) => {
  const navigate = useNavigate();
  const [universities, setUniversities] = useState<UniversityItem[]>([]);
  const [gosts, setGosts] = useState<GostItem[]>([]);
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [universityId, setUniversityId] = useState<number | undefined>();
  const [templateVersionId, setTemplateVersionId] = useState<number | undefined>();
  const [gostId, setGostId] = useState<number | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [unis, gs] = await Promise.all([fetchUniversities(), fetchGosts()]);
        if (!cancelled) {
          setUniversities(unis);
          setGosts(gs);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Ошибка загрузки справочников");
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function loadTemplates() {
      if (!universityId) {
        setTemplates([]);
        return;
      }
      try {
        const ts = await fetchTemplates(universityId);
        if (!cancelled) {
          setTemplates(ts);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Ошибка загрузки шаблонов");
      }
    }
    void loadTemplates();
    return () => {
      cancelled = true;
    };
  }, [universityId]);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    if (!/\.(doc|docx)$/i.test(f.name)) {
      setError("Поддерживаются только файлы DOC/DOCX");
      return;
    }
    if (f.size > 20 * 1024 * 1024) {
      setError("Файл слишком большой (максимум 20 МБ)");
      return;
    }
    setError(null);
    setFile(f);
  }

  async function handleStartCheck() {
    if (!file || !templateVersionId) {
      setError("Выберите шаблон и загрузите файл");
      return;
    }
    if (me.credits_available <= 0) {
      setError("Недостаточно кредитов. Пополните баланс в профиле.");
      return;
    }
    try {
      setUploading(true);
      const uploaded = await uploadFile(file);
      setUploading(false);
      setStarting(true);
      const check = await startCheck({
        template_version_id: templateVersionId,
        gost_id: gostId,
        file_id: uploaded.file_id
      });
      navigate(`/checks/${check.id}`);
    } catch (e) {
      setUploading(false);
      setStarting(false);
      setError(e instanceof Error ? e.message : "Не удалось запустить проверку");
    }
  }

  return (
    <div className="glass-card" style={{ padding: 16 }}>
      <div className="page-section-title">Настройки проверки</div>
      <div className="page-section-description">
        Сначала выберите вуз и шаблон проверки, затем загрузите документ в формате DOCX.
      </div>

      <div className="spacer-12" />

      <div className="field-label">ВУЗ</div>
      <select
        value={universityId ?? ""}
        onChange={(e) => {
          const value = e.target.value;
          setUniversityId(value ? Number(value) : undefined);
          setTemplateVersionId(undefined);
        }}
        style={{ width: "100%", minHeight: 40, borderRadius: 12, padding: "6px 10px" }}
      >
        <option value="">Выберите вуз</option>
        {universities.map((u) => (
          <option key={u.id} value={u.id}>
            {u.name}
          </option>
        ))}
      </select>

      <div className="spacer-12" />

      <div className="field-label">Шаблон проверки</div>
      <select
        value={templateVersionId ?? ""}
        onChange={(e) => setTemplateVersionId(e.target.value ? Number(e.target.value) : undefined)}
        style={{ width: "100%", minHeight: 40, borderRadius: 12, padding: "6px 10px" }}
      >
        <option value="">Выберите шаблон</option>
        {templates.map((t) => (
          <option key={t.id} value={t.id}>
            {t.name} · {t.type_work} · {t.year || "год не указан"}
          </option>
        ))}
      </select>

      <div className="spacer-12" />

      <div className="field-label">ГОСТ / стиль</div>
      <select
        value={gostId ?? ""}
        onChange={(e) => setGostId(e.target.value ? Number(e.target.value) : null)}
        style={{ width: "100%", minHeight: 40, borderRadius: 12, padding: "6px 10px" }}
      >
        <option value="">Автоматически по шаблону</option>
        {gosts.map((g) => (
          <option key={g.id} value={g.id}>
            {g.name}
          </option>
        ))}
      </select>

      <div className="spacer-16" />

      <div className="field-label">Файл работы (DOC/DOCX, до 20 МБ)</div>
      <label className="upload-zone">
        <div>Перетащите файл сюда или нажмите, чтобы выбрать</div>
        <div className="upload-zone-button">
          <span className="secondary-btn">
            <Icon name="file-text" className="bottom-nav-icon" /> Выбрать файл
          </span>
        </div>
        <input type="file" accept=".doc,.docx" onChange={handleFileChange} />
        {file && (
          <div style={{ marginTop: 8, fontSize: 12 }}>
            Выбран файл: <strong>{file.name}</strong>{" "}
            <span className="text-muted">({(file.size / (1024 * 1024)).toFixed(1)} МБ)</span>
          </div>
        )}
      </label>

      <div className="spacer-16" />

      <div className="field-label">Кредиты</div>
      <div className="credits-badge">
        Доступно проверок: <strong>{me.credits_available}</strong>
      </div>

      {error && (
        <div style={{ marginTop: 10, fontSize: 12, color: "#b91c1c" }}>
          <strong>Ошибка:</strong> {error}
        </div>
      )}

      <div className="spacer-16" />

      <button
        className="primary-btn"
        style={{ width: "100%" }}
        disabled={!file || !templateVersionId || uploading || starting}
        onClick={handleStartCheck}
      >
        {uploading
          ? "Загружаем файл…"
          : starting
          ? "Запускаем проверку…"
          : "Запустить проверку и списать 1 кредит"}
      </button>
    </div>
  );
};



