import ClueFields from "./ClueFields";
import { useState, type FormEvent } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  ChevronDown,
  Cpu,
  ListFilter,
  Loader2,
  Plus,
  Search,
  ShieldCheck,
  Target,
  Users,
} from "lucide-react";
import { t, getPreferences } from "../i18n";
import { api } from "../api";
import type { NameVariant } from "../types";
import type { Brief } from "../types";
import { languages, split } from "../constants";
import { Field, BudgetFields } from "./ui";
export default function NewResearch({
  onCreate,
  busy,
  configured,
  openSettings,
}: {
  onCreate: (brief: Brief) => void;
  busy: boolean;
  configured: boolean;
  openSettings: () => void;
}) {
  const [brief, setBrief] = useState<Brief>({
    name: "",
    aliases: [],
    expand_names: true,
    surname_change: "unknown",
    previous_names: [],
    output_language: getPreferences().language,
    city: "",
    country: "",
    year_from: null,
    year_to: null,
    context: "",
    evidence_clues: [],
    languages: ["en", "ru", "uk"],
    include_domains: [],
    exclude_domains: [],
    seed_urls: [],
    freshness: "all",
    budget: { minutes: 30, queries: 40, pages: 80, rounds: 5 },
  });
  const [variants, setVariants] = useState<NameVariant[]>([]);
  const [previewing, setPreviewing] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [previewKey, setPreviewKey] = useState("");
  const [advanced, setAdvanced] = useState(false);
  const set = <K extends keyof Brief>(key: K, value: Brief[K]) =>
    setBrief((b) => ({ ...b, [key]: value }));
  const submit = (e: FormEvent) => {
    e.preventDefault();
    onCreate({ ...brief, output_language: getPreferences().language });
  };
  return (
    <div className="new-research">
      <section className="hero">
        <div className="eyebrow">
          <span /> {t("ЛОКАЛЬНЫЙ ИИ · ОТКРЫТЫЕ ИСТОЧНИКИ")}
        </div>
        <h1>
          {t("За именем —")}
          <br />
          <span>{t("проверяемые факты.")}</span>
        </h1>
        <p>
          {t("Находите публичные профили и упоминания.")}
          <br className="desktop" />{" "}
          {t("Сравнивайте совпадения. Возвращайтесь к первоисточнику.")}
        </p>
        <div className="orbit" aria-hidden="true">
          <div className="orbit-circle outer" />
          <div className="orbit-circle inner" />
          <span className="orbit-point a" />
          <span className="orbit-point b" />
          <span className="orbit-point c" />
          <Target size={38} />
          <span className="orbit-label">CONNECT THE EVIDENCE</span>
        </div>
      </section>
      <form onSubmit={submit} className="research-form">
        <div className="section-heading">
          <div className="step">01</div>
          <div>
            <h2>{t("С кого начнём?")}</h2>
            <p>
              {t(
                "Достаточно имени. Дополнительные ориентиры помогут отделить тёзок.",
              )}
            </p>
          </div>
        </div>
        <Field label={t("Имя и фамилия")}>
          {(id) => (
            <div className="input-icon">
              <Search size={19} />
              <input
                id={id}
                required
                minLength={2}
                maxLength={160}
                placeholder={t("Например, имя вашего одноклассника")}
                value={brief.name}
                onChange={(e) => set("name", e.target.value)}
                autoComplete="off"
              />
            </div>
          )}
        </Field>
        <div className="grid two">
          <Field
            label={t("Город")}
            hint={t(
              "Required connection, including earlier life. Add the region to distinguish namesakes.",
              "Обязательная связь, в том числе в прошлом. Добавьте область для различения городов.",
            )}
          >
            {(id) => (
              <input
                id={id}
                maxLength={120}
                placeholder={t("Город учёбы, работы или рождения")}
                value={brief.city}
                onChange={(e) => set("city", e.target.value)}
              />
            )}
          </Field>
          <Field label={t("Страна")}>
            {(id) => (
              <input
                id={id}
                maxLength={120}
                placeholder={t("Если известна")}
                value={brief.country}
                onChange={(e) => set("country", e.target.value)}
              />
            )}
          </Field>
        </div>
        <Field
          label={t("Что ещё вы знаете?")}
          hint={t("Отмечайте, какие сведения точные, а какие — предположение.")}
        >
          {(id) => (
            <textarea
              id={id}
              rows={3}
              maxLength={6000}
              placeholder={t(
                "Место учёбы, профессия, публичный проект или известная ссылка…",
              )}
              value={brief.context}
              onChange={(e) => set("context", e.target.value)}
            />
          )}
        </Field>
        <div className="field">
          <label>{t("Языки поиска")}</label>
          <div className="chips">
            {languages.slice(0, advanced ? 12 : 6).map(([code, name]) => (
              <button
                key={code}
                type="button"
                className={`chip ${brief.languages.includes(code) ? "selected" : ""}`}
                aria-pressed={brief.languages.includes(code)}
                onClick={() =>
                  set(
                    "languages",
                    brief.languages.includes(code)
                      ? brief.languages.length > 1
                        ? brief.languages.filter((l) => l !== code)
                        : brief.languages
                      : [...brief.languages, code],
                  )
                }
              >
                {brief.languages.includes(code) && <Check size={13} />} {name}
              </button>
            ))}
          </div>
        </div>
        <button
          type="button"
          className="advanced-button"
          aria-expanded={advanced}
          onClick={() => setAdvanced(!advanced)}
        >
          <ListFilter size={17} />{" "}
          {advanced
            ? t("Скрыть дополнительные фильтры")
            : t("Варианты имени, годы и источники")}
          <ChevronDown size={16} className={advanced ? "rotated" : ""} />
        </button>
        {advanced && (
          <div className="advanced-fields">
            <Field
              label={t("Другие варианты имени")}
              hint={t("Через запятую. Только известные вам варианты.")}
            >
              {(id) => (
                <input
                  id={id}
                  defaultValue={brief.aliases.join(", ")}
                  placeholder={t("Иное написание или транслитерация")}
                  onChange={(e) => set("aliases", split(e.target.value))}
                />
              )}
            </Field>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={brief.expand_names}
                onChange={(e) => set("expand_names", e.target.checked)}
              />
              {t(
                "Explore spelling and transliteration variants",
                "Искать варианты написания и транслитерации",
              )}
            </label>
            <Field
              label={t(
                "Could the surname have changed?",
                "Могла ли измениться фамилия?",
              )}
              hint={t(
                "This can apply to anyone. We use known previous names; never invent a married surname.",
                "Это возможно у любого человека. Используем известные прежние имена, не придумываем фамилию после брака.",
              )}
            >
              {(id) => (
                <select
                  id={id}
                  value={brief.surname_change}
                  onChange={(e) =>
                    set(
                      "surname_change",
                      e.target.value as Brief["surname_change"],
                    )
                  }
                >
                  <option value="unknown">{t("Unknown", "Неизвестно")}</option>
                  <option value="possible">
                    {t("Possibly changed", "Могла измениться")}
                  </option>
                  <option value="known">
                    {t("I know a previous name", "Известно прежнее имя")}
                  </option>
                </select>
              )}
            </Field>
            {brief.surname_change !== "unknown" && (
              <Field
                label={t(
                  "Known previous full names",
                  "Известные прежние полные имена",
                )}
                hint={t(
                  "Comma-separated. Leave blank if unknown; add school or work clues above instead.",
                  "Через запятую. Если неизвестны, оставьте пустым и добавьте сведения об учёбе или работе выше.",
                )}
              >
                {(id) => (
                  <input
                    id={id}
                    defaultValue={brief.previous_names.join(", ")}
                    onChange={(e) =>
                      set("previous_names", split(e.target.value))
                    }
                  />
                )}
              </Field>
            )}
            <button
              type="button"
              className="button secondary"
              disabled={brief.name.trim().length < 2 || previewing}
              onClick={async () => {
                setPreviewing(true);
                setPreviewError("");
                try {
                  const r = await api<{ variants: NameVariant[] }>(
                    "/names/preview",
                    "POST",
                    brief,
                  );
                  setVariants(r.variants);
                  setPreviewKey(
                    JSON.stringify([
                      brief.name,
                      brief.aliases,
                      brief.previous_names,
                      brief.expand_names,
                    ]),
                  );
                } catch (e) {
                  setPreviewError((e as Error).message);
                } finally {
                  setPreviewing(false);
                }
              }}
            >
              {previewing && <Loader2 size={15} className="spin" />}
              {t(
                "Preview spelling hypotheses",
                "Посмотреть варианты написания",
              )}
            </button>
            {previewError && <p role="alert">{previewError}</p>}
            {variants.length > 0 &&
              previewKey ===
                JSON.stringify([
                  brief.name,
                  brief.aliases,
                  brief.previous_names,
                  brief.expand_names,
                ]) && (
                <div className="name-preview">
                  <p className="small-muted">
                    {t(
                      "Starting hypotheses, not verified aliases. The local model can propose additional variants during research.",
                      "Начальные гипотезы, не подтверждённые имена. Локальная модель может предложить дополнительные варианты во время поиска.",
                    )}
                  </p>
                  <div className="chips">
                    {variants.map((v) => (
                      <span
                        className="chip"
                        key={v.name}
                        title={
                          v.origin === "supplied"
                            ? t("Provided by you", "Указано вами")
                            : t("Hypothesis", "Гипотеза")
                        }
                      >
                        {v.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            <ClueFields
              value={brief.evidence_clues}
              onChange={(v) => set("evidence_clues", v)}
            />
            <div className="grid two">
              <Field label={t("Год рождения — от")}>
                {(id) => (
                  <input
                    id={id}
                    type="number"
                    min={1850}
                    max={2100}
                    value={brief.year_from ?? ""}
                    onChange={(e) =>
                      set("year_from", e.target.value ? +e.target.value : null)
                    }
                  />
                )}
              </Field>
              <Field label={t("Год рождения — до")}>
                {(id) => (
                  <input
                    id={id}
                    type="number"
                    min={1850}
                    max={2100}
                    value={brief.year_to ?? ""}
                    onChange={(e) =>
                      set("year_to", e.target.value ? +e.target.value : null)
                    }
                  />
                )}
              </Field>
            </div>
            <p className="small-muted">
              {t(
                "Годы — ваши ориентиры для поиска, а не подтверждённые сведения о найденном человеке.",
              )}
            </p>
            <div className="grid two">
              <Field label={t("Искать только на доменах")}>
                {(id) => (
                  <input
                    id={id}
                    placeholder="example.org, university.edu"
                    defaultValue={brief.include_domains.join(", ")}
                    onChange={(e) =>
                      set("include_domains", split(e.target.value))
                    }
                  />
                )}
              </Field>
              <Field label={t("Исключить домены")}>
                {(id) => (
                  <input
                    id={id}
                    placeholder={t("Через запятую")}
                    defaultValue={brief.exclude_domains.join(", ")}
                    onChange={(e) =>
                      set("exclude_domains", split(e.target.value))
                    }
                  />
                )}
              </Field>
            </div>
            <Field
              label={t("Начальные ссылки")}
              hint={t("Публичные HTML-страницы. Каждая ссылка с новой строки.")}
            >
              {(id) => (
                <textarea
                  id={id}
                  rows={2}
                  placeholder="https://…"
                  defaultValue={brief.seed_urls.join("\n")}
                  onChange={(e) =>
                    set(
                      "seed_urls",
                      e.target.value
                        .split("\n")
                        .map((v) => v.trim())
                        .filter(Boolean),
                    )
                  }
                />
              )}
            </Field>
            <Field
              label={t("Свежесть поисковой выдачи")}
              hint={t(
                "Фильтр поисковой системы; дата публикации не всегда известна.",
              )}
            >
              {(id) => (
                <select
                  id={id}
                  value={brief.freshness}
                  onChange={(e) => set("freshness", e.target.value)}
                >
                  <option value="all">{t("За всё время")}</option>
                  <option value="d">{t("Сутки")}</option>
                  <option value="w">{t("Неделя")}</option>
                  <option value="m">{t("Месяц")}</option>
                  <option value="y">{t("Год")}</option>
                </select>
              )}
            </Field>
          </div>
        )}
        <div className="form-divider" />
        <div className="section-heading">
          <div className="step">02</div>
          <div>
            <h2>{t("Насколько глубоко искать?")}</h2>
            <p>
              {t(
                "Поиск остановится при первом достигнутом лимите. Бюджет можно увеличить.",
              )}
            </p>
          </div>
        </div>
        <div className="presets">
          {[
            {
              title: t("Быстрый"),
              desc: t("10 минут"),
              value: { minutes: 10, queries: 12, pages: 20, rounds: 2 },
            },
            {
              title: t("Тщательный"),
              desc: t("30 минут"),
              value: { minutes: 30, queries: 40, pages: 80, rounds: 5 },
            },
            {
              title: t("Глубокий"),
              desc: t("2 часа"),
              value: { minutes: 120, queries: 150, pages: 250, rounds: 15 },
            },
          ].map((p) => (
            <button
              type="button"
              key={p.title}
              className={`preset ${JSON.stringify(brief.budget) === JSON.stringify(p.value) ? "active" : ""}`}
              onClick={() => set("budget", p.value)}
            >
              <span>{p.title}</span>
              <small>{p.desc}</small>
            </button>
          ))}
        </div>
        <BudgetFields value={brief.budget} onChange={(v) => set("budget", v)} />
        {!configured && (
          <div className="notice">
            <Cpu size={17} />
            <span>
              {t(
                "Choose a local model in settings before starting.",
                "Перед запуском выберите локальную модель в настройках.",
              )}
            </span>
            <button type="button" onClick={openSettings}>
              {t("Подключить")}
              <ArrowUpRight size={14} />
            </button>
          </div>
        )}
        <div className="form-bottom">
          <p>
            <ShieldCheck size={16} /> {t("ИИ и история — на вашем Mac.")}
            <br />
            <span>
              {t("Поисковые запросы передаются выбранным поисковым системам.")}
            </span>
          </p>
          <button type="submit" className="button primary" disabled={busy}>
            {busy ? <Loader2 size={17} className="spin" /> : <Plus size={17} />}{" "}
            {t("Создать поиск")}
            <ArrowRight size={17} />
          </button>
        </div>
      </form>
      <div className="principles">
        <span>
          <BookOpen size={16} /> {t("Источники для каждого факта")}
        </span>
        <span>
          <Users size={16} /> {t("Тёзки остаются разными людьми")}
        </span>
        <span>
          <Cpu size={16} /> {t("Без облачного ИИ")}
        </span>
      </div>
    </div>
  );
}
