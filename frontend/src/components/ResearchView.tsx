import { useState } from "react";
import {
  ArrowDownToLine,
  ArrowUpRight,
  Check,
  CircleDot,
  Clock3,
  Cpu,
  Globe2,
  ListFilter,
  Loader2,
  Pause,
  Play,
  Plus,
  Search,
  ShieldCheck,
  Target,
  Trash2,
  Users,
  X,
  AlertCircle,
  ExternalLink,
  CheckCircle2,
  CircleHelp,
} from "lucide-react";
import type { Candidate, Detail, Source } from "../types";
import {
  languages,
  statusName,
  split,
  duration,
  date,
  host,
} from "../constants";
function CandidateCard({
  candidate,
  source,
  review,
}: {
  candidate: Candidate;
  source?: Source;
  review: (status: Candidate["status"]) => void;
}) {
  const v = candidate.value;
  return (
    <article className={`candidate-card ${candidate.status}`}>
      <div className="candidate-heading">
        <div className="avatar">
          {v.name
            .split(" ")
            .slice(0, 2)
            .map((s) => s[0])
            .join("")}
        </div>
        <div>
          <h3>{v.name}</h3>
          <p>{v.description}</p>
        </div>
        <span className={`review-label ${candidate.status}`}>
          {candidate.status === "confirmed"
            ? "Вы подтвердили"
            : candidate.status === "rejected"
              ? "Отклонён"
              : "Возможное совпадение"}
        </span>
      </div>
      {v.matches.length > 0 && (
        <div className="match-notes">
          {v.matches.map((m, i) => (
            <span key={i}>
              <CircleDot size={12} />
              {m}
            </span>
          ))}
        </div>
      )}
      {v.contradictions.length > 0 && (
        <div className="contradictions">
          <AlertCircle size={15} />
          <span>{v.contradictions.join(" · ")}</span>
        </div>
      )}
      <div className="facts">
        {v.facts.map((f, i) => (
          <div className="fact" key={i}>
            <p>
              <CheckCircle2 size={15} />
              {f.statement}
            </p>
            <blockquote>{f.quote}</blockquote>
          </div>
        ))}
      </div>
      <div className="candidate-footer">
        {source && (
          <a
            href={source.url}
            target="_blank"
            rel="noreferrer"
            className="source-link"
          >
            <Globe2 size={14} />
            {host(source.url)}
            <ArrowUpRight size={14} />
          </a>
        )}
        <div className="review-actions">
          <button
            className={candidate.status === "confirmed" ? "selected" : ""}
            onClick={() =>
              review(
                candidate.status === "confirmed" ? "unreviewed" : "confirmed",
              )
            }
          >
            <Check size={15} />
            Это он / она
          </button>
          <button
            className={candidate.status === "rejected" ? "selected" : ""}
            onClick={() =>
              review(
                candidate.status === "rejected" ? "unreviewed" : "rejected",
              )
            }
          >
            <X size={15} />
            Другой человек
          </button>
        </div>
      </div>
    </article>
  );
}

export default function ResearchView({
  job,
  action,
  review,
  refine,
  editBudget,
  remove,
  pending,
}: {
  job: Detail;
  action: (a: string) => void;
  review: (id: string, status: Candidate["status"]) => void;
  refine: (text: string) => Promise<boolean>;
  editBudget: () => void;
  remove: () => void;
  pending: boolean;
}) {
  const [tab, setTab] = useState("candidates");
  const [filter, setFilter] = useState("all");
  const [note, setNote] = useState("");
  const running = ["running", "queued"].includes(job.status);
  const elapsed =
    job.active_seconds +
    (job.status === "running"
      ? Math.max(0, (Date.now() - Date.parse(job.updated_at)) / 1000)
      : 0);
  const candidates = job.candidates.filter(
    (c) => filter === "all" || c.status === filter,
  );
  return (
    <div className="research-view">
      <div className="research-title">
        <div>
          <div className="eyebrow">ИССЛЕДОВАНИЕ · {date(job.created_at)}</div>
          <h1>{job.name}</h1>
          <p>
            {[job.brief.city, job.brief.country].filter(Boolean).join(" · ") ||
              "Публичные профили и упоминания"}
            <span className="title-languages">
              {job.brief.languages.map((l) => l.toUpperCase()).join(" / ")}
            </span>
          </p>
        </div>
        <div className="title-actions">
          <a className="button secondary" href={`/api/jobs/${job.id}/export`}>
            <ArrowDownToLine size={16} />
            Отчёт
          </a>
          <button
            disabled={pending}
            className={`button ${running ? "secondary" : "primary"}`}
            onClick={() => action(running ? "pause" : "start")}
          >
            {pending ? (
              <Loader2 size={16} className="spin" />
            ) : running ? (
              <Pause size={16} />
            ) : (
              <Play size={16} />
            )}{" "}
            {running
              ? "Пауза"
              : job.status === "draft"
                ? "Начать поиск"
                : "Продолжить"}
          </button>
        </div>
      </div>
      <div className="metrics">
        {[
          { label: "Запросов", value: job.stats.queries, icon: Search },
          {
            label: "Источников прочитано",
            value: job.stats.sources,
            icon: Globe2,
          },
          {
            label: "Возможных совпадений",
            value: job.stats.candidates,
            icon: Users,
          },
          { label: "Время работы", value: duration(elapsed), icon: Clock3 },
        ].map((m) => (
          <div className="metric" key={m.label}>
            <m.icon size={17} />
            <strong>{m.value}</strong>
            <span>{m.label}</span>
          </div>
        ))}
      </div>
      {(job.reason || running) && (
        <div className={`run-status ${job.status}`}>
          <span>
            {running ? (
              <Loader2 className="spin" size={18} />
            ) : job.status === "completed" ? (
              <CheckCircle2 size={18} />
            ) : (
              <CircleHelp size={18} />
            )}
          </span>
          <div>
            <strong>{statusName[job.status]}</strong>
            <p>
              {job.status === "running"
                ? job.events[0]?.message || "Подготовка поиска…"
                : job.reason}
            </p>
          </div>
          {running && <span className="live-indicator">LIVE</span>}
        </div>
      )}
      <div className="workspace-columns">
        <div className="results-column">
          <div className="tabs" role="tablist">
            {[
              ["candidates", "Совпадения", job.candidates.length],
              ["sources", "Источники", job.sources.length],
              ["queries", "План", job.queries.length],
              ["events", "Журнал", null],
            ].map(([key, title, count]) => (
              <button
                key={String(key)}
                role="tab"
                aria-selected={tab === key}
                className={tab === key ? "active" : ""}
                onClick={() => setTab(String(key))}
              >
                {title}
                {count !== null && <span>{count}</span>}
              </button>
            ))}
          </div>
          {tab === "candidates" && (
            <>
              <div className="result-tools">
                <span>Каждое совпадение требует вашей проверки</span>
                <select
                  aria-label="Фильтр совпадений"
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                >
                  <option value="all">Все</option>
                  <option value="unreviewed">Не проверены</option>
                  <option value="confirmed">Подтверждены вами</option>
                  <option value="rejected">Отклонены</option>
                </select>
              </div>
              {candidates.length ? (
                candidates.map((c) => (
                  <CandidateCard
                    key={c.id}
                    candidate={c}
                    source={job.sources.find((s) => s.id === c.source_id)}
                    review={(status) => review(c.id, status)}
                  />
                ))
              ) : (
                <div className="empty-results">
                  <div className="empty-icon">
                    <Users size={29} />
                  </div>
                  <h3>
                    {running
                      ? "Ищем обоснованные совпадения"
                      : job.status === "draft"
                        ? "Всё готово к первому поиску"
                        : "Совпадений пока нет"}
                  </h3>
                  <p>
                    {running
                      ? "Здесь появятся люди, для которых найдены цитаты на прочитанных страницах."
                      : job.status === "draft"
                        ? "Нажмите «Начать поиск». Приложение составит план и проверит доступные источники."
                        : "Посмотрите источники и журнал: отсутствие совпадений может означать недостаток данных или недоступность сайтов."}
                  </p>
                </div>
              )}
              <p className="evidence-note">
                <ShieldCheck size={14} />
                Цитаты проверены на присутствие в тексте. Их смысл и
                принадлежность человеку требуют проверки.
              </p>
            </>
          )}
          {tab === "sources" && (
            <div className="source-list">
              {job.sources.length ? (
                job.sources.map((s) => (
                  <article key={s.id} className="source-item">
                    <div className="source-icon">
                      <Globe2 size={20} />
                    </div>
                    <div>
                      <a href={s.url} target="_blank" rel="noreferrer">
                        {s.title || host(s.url)}
                        <ExternalLink size={13} />
                      </a>
                      <small>
                        {host(s.url)} · {date(s.fetched_at)}
                      </small>
                      {s.error && <p className="source-error">{s.error}</p>}
                    </div>
                    <span className={`source-state ${s.status}`}>
                      {s.status === "read" ? "Прочитан" : "Недоступен"}
                    </span>
                  </article>
                ))
              ) : (
                <div className="simple-empty">
                  Прочитанные и недоступные источники появятся здесь.
                </div>
              )}
            </div>
          )}
          {tab === "queries" && (
            <div className="query-list">
              {job.queries.length ? (
                job.queries.map((q, i) => (
                  <div key={q.id} className="query-item">
                    <span className="query-number">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <div>
                      <strong>{q.payload.query}</strong>
                      <p>{q.payload.reason}</p>
                      {q.error && <p className="source-error">{q.error}</p>}
                    </div>
                    <span className="query-language">{q.payload.language}</span>
                    <span title={q.state}>
                      {q.state === "done" ? (
                        <Check size={16} />
                      ) : q.state === "failed" ? (
                        <AlertCircle size={16} />
                      ) : q.state === "running" ? (
                        <Loader2 className="spin" size={16} />
                      ) : (
                        <Clock3 size={15} />
                      )}
                    </span>
                  </div>
                ))
              ) : (
                <div className="simple-empty">
                  Локальная модель составит план после запуска.
                </div>
              )}
            </div>
          )}
          {tab === "events" && (
            <div className="event-list">
              {job.events.map((e) => (
                <div key={e.id} className={`event ${e.level}`}>
                  <time>
                    {new Date(e.at).toLocaleTimeString("ru-RU", {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })}
                  </time>
                  <span className="event-dot" />
                  <p>{e.message}</p>
                </div>
              ))}
            </div>
          )}
        </div>
        <aside className="research-aside">
          <div className="aside-card">
            <div className="aside-title">
              <ListFilter size={17} />
              <h3>Параметры поиска</h3>
            </div>
            <div className="budget-meter">
              <div>
                <span>Время</span>
                <strong>
                  {duration(elapsed)} / {job.brief.budget.minutes} мин
                </strong>
              </div>
              <div className="meter">
                <span
                  style={{
                    width: `${Math.min(100, (elapsed / (job.brief.budget.minutes * 60)) * 100)}%`,
                  }}
                />
              </div>
            </div>
            <dl>
              <div>
                <dt>Запросы</dt>
                <dd>
                  {job.stats.queries} / {job.brief.budget.queries}
                </dd>
              </div>
              <div>
                <dt>Страницы, включая ошибки</dt>
                <dd>
                  {job.stats.pages} / {job.brief.budget.pages}
                </dd>
              </div>
              <div>
                <dt>Этапы планирования</dt>
                <dd>
                  {job.rounds} / {job.brief.budget.rounds}
                </dd>
              </div>
              <div>
                <dt>Языки</dt>
                <dd>
                  {job.brief.languages.map((l) => l.toUpperCase()).join(", ")}
                </dd>
              </div>
            </dl>
            <button
              className="button secondary full"
              disabled={running}
              onClick={editBudget}
            >
              Изменить бюджет
            </button>
            {running && (
              <small className="small-muted">
                Для изменения параметров поставьте поиск на паузу.
              </small>
            )}
          </div>
          <div className="aside-card">
            <div className="aside-title">
              <Target size={17} />
              <h3>Ваши ориентиры</h3>
            </div>
            <p className="context-text">
              {job.brief.context || "Дополнительные сведения не указаны."}
            </p>
            {job.brief.aliases.length > 0 && (
              <p className="small-muted">
                Варианты: {job.brief.aliases.join(", ")}
              </p>
            )}
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                if (await refine(note)) setNote("");
              }}
            >
              <label className="sr-only" htmlFor="refinement">
                Новое уточнение
              </label>
              <textarea
                id="refinement"
                rows={3}
                required
                minLength={2}
                maxLength={2000}
                disabled={running}
                placeholder={
                  running
                    ? "Приостановите поиск, чтобы добавить сведения"
                    : "Добавьте новое уточнение…"
                }
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
              <button
                disabled={running || note.trim().length < 2 || pending}
                className="button text full"
              >
                <Plus size={15} />
                Добавить ориентир
              </button>
            </form>
          </div>
          <div className="local-footnote">
            <Cpu size={19} />
            <div>
              <strong>Только локальный ИИ</strong>
              <p>
                {job.settings_snapshot.model ||
                  "Модель будет выбрана при запуске"}
              </p>
            </div>
          </div>
          <button className="delete-button" onClick={remove} disabled={running}>
            <Trash2 size={14} />
            Удалить исследование
          </button>
        </aside>
      </div>
    </div>
  );
}
