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
    city: "",
    country: "",
    year_from: null,
    year_to: null,
    context: "",
    languages: ["ru", "en"],
    include_domains: [],
    exclude_domains: [],
    seed_urls: [],
    freshness: "all",
    budget: { minutes: 30, queries: 40, pages: 80, rounds: 5 },
  });
  const [advanced, setAdvanced] = useState(false);
  const set = <K extends keyof Brief>(key: K, value: Brief[K]) =>
    setBrief((b) => ({ ...b, [key]: value }));
  const submit = (e: FormEvent) => {
    e.preventDefault();
    onCreate(brief);
  };
  return (
    <div className="new-research">
      <section className="hero">
        <div className="eyebrow">
          <span /> ЛОКАЛЬНЫЙ ИИ · ОТКРЫТЫЕ ИСТОЧНИКИ
        </div>
        <h1>
          За именем —<br />
          <span>проверяемые факты.</span>
        </h1>
        <p>
          Находите публичные профили и упоминания.
          <br className="desktop" /> Сравнивайте совпадения. Возвращайтесь к
          первоисточнику.
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
            <h2>С кого начнём?</h2>
            <p>
              Достаточно имени. Дополнительные ориентиры помогут отделить тёзок.
            </p>
          </div>
        </div>
        <Field label="Имя и фамилия">
          {(id) => (
            <div className="input-icon">
              <Search size={19} />
              <input
                id={id}
                required
                minLength={2}
                maxLength={160}
                placeholder="Например, имя вашего одноклассника"
                value={brief.name}
                onChange={(e) => set("name", e.target.value)}
                autoComplete="off"
              />
            </div>
          )}
        </Field>
        <div className="grid two">
          <Field label="Город" hint="Можно указать приблизительно">
            {(id) => (
              <input
                id={id}
                maxLength={120}
                placeholder="Город учёбы, работы или рождения"
                value={brief.city}
                onChange={(e) => set("city", e.target.value)}
              />
            )}
          </Field>
          <Field label="Страна">
            {(id) => (
              <input
                id={id}
                maxLength={120}
                placeholder="Если известна"
                value={brief.country}
                onChange={(e) => set("country", e.target.value)}
              />
            )}
          </Field>
        </div>
        <Field
          label="Что ещё вы знаете?"
          hint="Отмечайте, какие сведения точные, а какие — предположение."
        >
          {(id) => (
            <textarea
              id={id}
              rows={3}
              maxLength={6000}
              placeholder="Место учёбы, профессия, публичный проект или известная ссылка…"
              value={brief.context}
              onChange={(e) => set("context", e.target.value)}
            />
          )}
        </Field>
        <div className="field">
          <label>Языки поиска</label>
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
            ? "Скрыть дополнительные фильтры"
            : "Варианты имени, годы и источники"}
          <ChevronDown size={16} className={advanced ? "rotated" : ""} />
        </button>
        {advanced && (
          <div className="advanced-fields">
            <Field
              label="Другие варианты имени"
              hint="Через запятую. Только известные вам варианты."
            >
              {(id) => (
                <input
                  id={id}
                  defaultValue={brief.aliases.join(", ")}
                  placeholder="Иное написание или транслитерация"
                  onChange={(e) => set("aliases", split(e.target.value))}
                />
              )}
            </Field>
            <div className="grid two">
              <Field label="Год рождения — от">
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
              <Field label="Год рождения — до">
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
              Годы — ваши ориентиры для поиска, а не подтверждённые сведения о
              найденном человеке.
            </p>
            <div className="grid two">
              <Field label="Искать только на доменах">
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
              <Field label="Исключить домены">
                {(id) => (
                  <input
                    id={id}
                    placeholder="Через запятую"
                    defaultValue={brief.exclude_domains.join(", ")}
                    onChange={(e) =>
                      set("exclude_domains", split(e.target.value))
                    }
                  />
                )}
              </Field>
            </div>
            <Field
              label="Начальные ссылки"
              hint="Публичные HTML-страницы. Каждая ссылка с новой строки."
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
              label="Свежесть поисковой выдачи"
              hint="Фильтр поисковой системы; дата публикации не всегда известна."
            >
              {(id) => (
                <select
                  id={id}
                  value={brief.freshness}
                  onChange={(e) => set("freshness", e.target.value)}
                >
                  <option value="all">За всё время</option>
                  <option value="d">Сутки</option>
                  <option value="w">Неделя</option>
                  <option value="m">Месяц</option>
                  <option value="y">Год</option>
                </select>
              )}
            </Field>
          </div>
        )}
        <div className="form-divider" />
        <div className="section-heading">
          <div className="step">02</div>
          <div>
            <h2>Насколько глубоко искать?</h2>
            <p>
              Поиск остановится при первом достигнутом лимите. Бюджет можно
              увеличить.
            </p>
          </div>
        </div>
        <div className="presets">
          {[
            {
              title: "Быстрый",
              desc: "10 минут",
              value: { minutes: 10, queries: 12, pages: 20, rounds: 2 },
            },
            {
              title: "Тщательный",
              desc: "30 минут",
              value: { minutes: 30, queries: 40, pages: 80, rounds: 5 },
            },
            {
              title: "Глубокий",
              desc: "2 часа",
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
            <span>Перед запуском выберите модель LM Studio.</span>
            <button type="button" onClick={openSettings}>
              Подключить <ArrowUpRight size={14} />
            </button>
          </div>
        )}
        <div className="form-bottom">
          <p>
            <ShieldCheck size={16} /> ИИ и история — на вашем Mac.
            <br />
            <span>
              Поисковые запросы передаются выбранным поисковым системам.
            </span>
          </p>
          <button type="submit" className="button primary" disabled={busy}>
            {busy ? <Loader2 size={17} className="spin" /> : <Plus size={17} />}{" "}
            Создать поиск <ArrowRight size={17} />
          </button>
        </div>
      </form>
      <div className="principles">
        <span>
          <BookOpen size={16} /> Источники для каждого факта
        </span>
        <span>
          <Users size={16} /> Тёзки остаются разными людьми
        </span>
        <span>
          <Cpu size={16} /> Без облачного ИИ
        </span>
      </div>
    </div>
  );
}
