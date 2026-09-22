import SourceLinks from "./SourceLinks";
import ResearchActivity from "./ResearchActivity";
import ResearchConclusion from "./ResearchConclusion";
import EvidenceMeter from "./EvidenceMeter";
import ContinueDialog, { type Continuation } from "./ContinueDialog";
import { t, getPreferences, locale } from "../i18n";
import AnalysisPanel from "./AnalysisPanel";
import ReportDialog from "./ReportDialog";
import { useState } from "react";
import useResearchClock, { clockTime } from "../useResearchClock";
import { identityPresentation } from "../identityPresentation";
import {
  ArrowDownToLine,
  ArrowUpRight,
  Check,
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
} from "lucide-react";
import type { Candidate, Detail, Source, LinkDecision } from "../types";
import { languages, split, duration, date, host } from "../constants";
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
  const checked = candidate.assessment?.checked_facts || [];
  const identity = identityPresentation(candidate.assessment);
  const withheld = v.facts.filter(
    (_, i) => !checked.some((f) => f.index === i),
  );
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
          <p>
            {t(
              "Public profile · source-based review",
              "Публичный профиль · проверка по источнику",
            )}
          </p>
        </div>
        <span className={`review-label ${candidate.status}`}>
          {candidate.assessment?.review_outdated
            ? t("Review needs updating", "Нужно обновить оценку")
            : candidate.status === "rejected"
              ? t("Отклонён")
              : candidate.status === "confirmed" && identity.accepted
                ? t("Вы подтвердили")
                : identity.label}
        </span>
      </div>
      {!identity.accepted && (
        <p className="identity-unconfirmed-note">
          {t(
            "This is a research lead, not an identified match. Details below belong to the person described by this source; they have not been attributed to the person you are looking for.",
            "Это зацепка для проверки, а не найденный человек. Сведения ниже относятся к человеку из источника; их принадлежность тому, кого вы ищете, не установлена.",
          )}
          {candidate.status === "confirmed" &&
            !candidate.assessment?.review_outdated && (
              <>
                {" "}
                {t(
                  "You marked this record as the person; source-based criteria remain separate.",
                  "Вы отметили эту запись как нужного человека; подтверждение условий источниками оценивается отдельно.",
                )}
              </>
            )}
        </p>
      )}
      <EvidenceMeter assessment={candidate.assessment} />
      {candidate.assessment?.review_outdated && (
        <p className="review-stale">
          {t(
            "Criteria changed after your review. Please recheck this card.",
            "Критерии изменились после вашей оценки. Проверьте карточку заново.",
          )}
        </p>
      )}
      {candidate.assessment?.note && (
        <div className="candidate-ai-note">
          <strong>{t("AI interpretation", "Комментарий ИИ")}</strong>
          <p>{candidate.assessment.note}</p>
          <small>
            {t("Claims: ", "Утверждения: ")}
            {candidate.assessment.note_facts.map((i) => (
              <a key={i} href={`#fact-${candidate.id}-${i}`}>
                [{i + 1}]{" "}
              </a>
            ))}
          </small>
        </div>
      )}
      {!!candidate.assessment?.flags.length && (
        <div className="contradictions">
          <AlertCircle size={15} />
          <span>{candidate.assessment.flags.join(" · ")}</span>
        </div>
      )}
      {!candidate.assessment?.model_reviewed && (
        <p className="review-stale">
          {t(
            "Semantic review is pending. Continue research to check these claims against their source.",
            "Смысловая проверка ещё не выполнена. Продолжите исследование, чтобы проверить утверждения по источнику.",
          )}
        </p>
      )}
      {checked.length > 0 && (
        <h4 className="profile-overview-title">
          {t(
            identity.accepted
              ? "Public work & education · sourced overview"
              : "What this source says about the named person",
            identity.accepted
              ? "Публичная деятельность и образование · по источнику"
              : "Что источник сообщает о человеке с этим именем",
          )}
        </h4>
      )}
      <div className="facts">
        {checked.map((f) => (
          <div
            className="fact"
            id={`fact-${candidate.id}-${f.index}`}
            key={f.index}
          >
            <p>
              <CheckCircle2 size={15} />
              <span>
                [{f.index + 1}] {f.statement}
              </span>
            </p>
            <blockquote>{f.quote}</blockquote>
            {source && (
              <a
                className="source-link"
                href={source.url}
                target="_blank"
                rel="noreferrer"
              >
                {host(source.url)}
                <ExternalLink size={12} />
              </a>
            )}
          </div>
        ))}
      </div>
      {withheld.length > 0 && (
        <details className="withheld-claims">
          <summary>
            {withheld.length}{" "}
            {t(
              "claims withheld from the overview",
              "утверждений не включено в обзор",
            )}
          </summary>
          <p>
            {t(
              "Original extraction. These claims are unreviewed, ambiguous or unsupported; they do not increase the match assessment.",
              "Исходное извлечение. Утверждения не проверены, неоднозначны или не поддержаны источником; они не усиливают оценку совпадения.",
            )}
          </p>
          {withheld.map((f, i) => (
            <div key={i}>
              <p>{f.statement}</p>
              <blockquote>{f.quote}</blockquote>
            </div>
          ))}
        </details>
      )}
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
                candidate.status === "confirmed" &&
                  !candidate.assessment?.review_outdated
                  ? "unreviewed"
                  : "confirmed",
              )
            }
          >
            <Check size={15} />
            {candidate.assessment?.review_outdated
              ? t("Confirm again", "Подтвердить заново")
              : t("Это он / она")}
          </button>
          <button
            className={candidate.status === "rejected" ? "selected" : ""}
            onClick={() =>
              review(
                candidate.status === "rejected" &&
                  !candidate.assessment?.review_outdated
                  ? "unreviewed"
                  : "rejected",
              )
            }
          >
            <X size={15} />
            {t("Другой человек")}
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
  continueResearch,
  error,
  remove,
  pending,
  initialTab = "candidates",
  reviewLink,
}: {
  initialTab?: string;
  reviewLink: (decision: LinkDecision) => void;
  job: Detail;
  action: (a: string) => void;
  review: (id: string, status: Candidate["status"]) => void;
  refine: (text: string) => Promise<boolean>;
  editBudget: () => void;
  continueResearch: (value: Continuation) => Promise<boolean>;
  error: string;
  remove: () => void;
  pending: boolean;
}) {
  const [tab, setTab] = useState(initialTab);
  const [reportOpen, setReportOpen] = useState(false);
  const [continueOpen, setContinueOpen] = useState(false);
  const [refining, setRefining] = useState(false);
  const [filter, setFilter] = useState("active");
  const [note, setNote] = useState("");
  const running = ["running", "queued"].includes(job.status);
  const elapsed = useResearchClock(job);
  const needsAllowance =
    job.status === "completed" || !!job.continuation?.blocked_by.length;
  const candidates = job.candidates.filter(
    (c) =>
      filter === "all" ||
      (filter === "active"
        ? !c.assessment?.excluded &&
          c.status !== "rejected" &&
          !["unresolved", "conflicting"].includes(
            c.assessment?.identity_status || "",
          )
        : filter === "unresolved" || filter === "conflicting"
          ? c.assessment?.identity_status === filter &&
            !c.assessment?.excluded &&
            c.status !== "rejected"
          : filter === "archived"
            ? c.assessment?.excluded
            : c.status === filter),
  );
  return (
    <div className="research-view">
      {continueOpen && (
        <ContinueDialog
          job={job}
          refining={refining}
          pending={pending}
          close={() => setContinueOpen(false)}
          save={continueResearch}
          error={error}
        />
      )}
      {reportOpen && (
        <ReportDialog id={job.id} close={() => setReportOpen(false)} />
      )}
      <div className="research-title">
        <div>
          <div className="eyebrow">
            {t("ИССЛЕДОВАНИЕ ·")}
            {date(job.created_at)}
          </div>
          <h1>{job.name}</h1>
          <p>
            {[job.brief.city, job.brief.country].filter(Boolean).join(" · ") ||
              t("Публичные профили и упоминания")}
            <span className="title-languages">
              {job.brief.languages.map((l) => l.toUpperCase()).join(" / ")}
            </span>
          </p>
        </div>
        <div className="title-actions">
          <button
            className="button secondary"
            onClick={() => setReportOpen(true)}
          >
            <ArrowDownToLine size={16} />
            {t("Отчёт")}
          </button>
          <button
            disabled={pending}
            className={`button ${running ? "secondary" : "primary"}`}
            onClick={() => {
              if (!running && needsAllowance) {
                setRefining(false);
                setContinueOpen(true);
              } else action(running ? "pause" : "start");
            }}
          >
            {pending ? (
              <Loader2 size={16} className="spin" />
            ) : running ? (
              <Pause size={16} />
            ) : (
              <Play size={16} />
            )}{" "}
            {running
              ? t("Пауза")
              : job.status === "draft"
                ? t("Начать поиск")
                : needsAllowance
                  ? t("Continue search", "Продолжить поиск")
                  : t("Продолжить")}
          </button>
        </div>
      </div>
      <div className="metrics">
        {[
          { label: t("Запросов"), value: job.stats.queries, icon: Search },
          {
            label: t("Источников прочитано"),
            value: job.stats.sources,
            icon: Globe2,
          },
          {
            label: t("Records to check", "Записей для проверки"),
            value: job.stats.candidates,
            icon: Users,
          },
          { label: t("Время работы"), value: clockTime(elapsed), icon: Clock3 },
        ].map((m) => (
          <div className="metric" key={m.label}>
            <m.icon size={17} />
            <strong
              className={m.icon === Clock3 ? "research-clock" : undefined}
              role={m.icon === Clock3 ? "timer" : undefined}
              aria-label={m.icon === Clock3 ? m.label : undefined}
            >
              {m.value}
            </strong>
            <span>{m.label}</span>
          </div>
        ))}
      </div>
      <ResearchActivity job={job} />
      <ResearchConclusion job={job} />
      <SourceLinks
        job={job}
        review={reviewLink}
        disabled={running || pending}
      />
      <div className="workspace-columns">
        <div className="results-column">
          <div className="tabs" role="tablist">
            {[
              ["candidates", t("Совпадения"), job.candidates.length],
              ["sources", t("Источники"), job.sources.length],
              ["queries", t("План"), job.queries.length],
              ["events", t("Журнал"), null],
              ["analysis", t("Analysis", "Анализ"), null],
              ["history", t("History", "История"), job.revisions?.length || 1],
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
          {tab === "analysis" && <AnalysisPanel job={job} />}
          {tab === "history" && (
            <div className="revision-history">
              <h3>
                {t(
                  "One project, continuing research",
                  "Один проект, продолжающийся поиск",
                )}
              </h3>
              <p>
                {t(
                  "Every criteria change is saved. ZIP includes the offline report, quotations, links and previous assessments. Findings stay separate until you review them.",
                  "Каждое изменение критериев сохранено. ZIP содержит офлайн-отчёт, цитаты, ссылки и прежние оценки. Найденные карточки остаются раздельными до вашей проверки.",
                )}
              </p>
              <button
                className="button secondary"
                onClick={() => setReportOpen(true)}
              >
                {t("Export project archive", "Скачать архив проекта")}
              </button>
              {job.revisions?.map((r) => (
                <details key={r.number}>
                  <summary>
                    <strong>
                      {t("Criteria", "Критерии")} v{r.number}
                    </strong>{" "}
                    · {date(r.at)}
                  </summary>
                  <p>
                    {r.brief.name} · {r.brief.aliases.join(", ")}
                  </p>
                  <p>
                    {r.brief.context ||
                      t(
                        "No additional context",
                        "Без дополнительного контекста",
                      )}
                  </p>
                  {r.brief.evidence_clues?.map((c, i) => (
                    <p key={i}>
                      {c.kind}: {c.text}
                    </p>
                  ))}
                  <p>
                    {t("Languages", "Языки")}: {r.brief.languages.join(", ")}
                  </p>
                  <p>
                    {t(
                      "Include / exclude domains",
                      "Включённые / исключённые домены",
                    )}
                    : {r.brief.include_domains.join(", ") || "—"} /{" "}
                    {r.brief.exclude_domains.join(", ") || "—"}
                  </p>
                </details>
              ))}
            </div>
          )}
          {tab === "candidates" && (
            <>
              <div className="result-tools">
                <span>
                  {t(
                    "Every record needs an identity check",
                    "Каждая запись требует проверки личности",
                  )}
                </span>
                <select
                  aria-label={t("Фильтр совпадений")}
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                >
                  <option value="active">
                    {t("Meet required criteria", "Соответствуют критериям")}
                  </option>
                  <option value="unresolved">
                    {t("Connection unverified", "Связь не подтверждена")} (
                    {job.conclusion?.unresolved_identity || 0})
                  </option>
                  <option value="conflicting">
                    {t("Criteria conflicts", "Противоречат критериям")} (
                    {job.conclusion?.conflicting_identity || 0})
                  </option>
                  <option value="archived">
                    {t("Archived by filters", "В архиве по фильтрам")}
                  </option>
                  <option value="all">{t("Все")}</option>
                  <option value="unreviewed">{t("Не проверены")}</option>
                  <option value="confirmed">{t("Подтверждены вами")}</option>
                  <option value="rejected">{t("Отклонены")}</option>
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
                      ? t("Ищем обоснованные совпадения")
                      : job.status === "draft"
                        ? t("Всё готово к первому поиску")
                        : job.conclusion?.linked_matches && filter === "active"
                          ? t(
                              "Combined evidence is shown above",
                              "Сводные свидетельства показаны выше",
                            )
                          : t("Совпадений пока нет")}
                  </h3>
                  <p>
                    {running
                      ? t(
                          "Only candidates with sourced support for every required criterion appear here. Unverified connections remain in their own list.",
                          "Здесь появятся кандидаты с подтверждением каждого обязательного критерия. Неподтверждённые связи остаются в отдельном списке.",
                        )
                      : job.status === "draft"
                        ? t(
                            "Нажмите «Начать поиск». Приложение составит план и проверит доступные источники.",
                          )
                        : job.conclusion?.linked_matches && filter === "active"
                          ? t(
                              "Original cards remain separate. Their combined criteria are shown in Evidence across sources.",
                              "Исходные карточки сохранены отдельно. Общие критерии показаны в блоке сопоставления источников.",
                            )
                          : t(
                              "Посмотрите источники и журнал: отсутствие совпадений может означать недостаток данных или недоступность сайтов.",
                            )}
                  </p>
                </div>
              )}
              <p className="evidence-note">
                <ShieldCheck size={14} />
                {t(
                  "Цитаты проверены на присутствие в тексте. Их смысл и принадлежность человеку требуют проверки.",
                )}
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
                      {s.error && <p className="source-error">{t(s.error)}</p>}
                    </div>
                    <span className={`source-state ${s.status}`}>
                      {s.status === "read" ? t("Прочитан") : t("Недоступен")}
                    </span>
                  </article>
                ))
              ) : (
                <div className="simple-empty">
                  {t("Прочитанные и недоступные источники появятся здесь.")}
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
                      {q.error && <p className="source-error">{t(q.error)}</p>}
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
                  {t("Локальная модель составит план после запуска.")}
                </div>
              )}
            </div>
          )}
          {tab === "events" && (
            <div className="event-list">
              {job.events.map((e) => (
                <div key={e.id} className={`event ${e.level}`}>
                  <time>
                    {new Date(e.at).toLocaleTimeString(locale(), {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })}
                  </time>
                  <span className="event-dot" />
                  <div>
                    {e.level === "model" && (
                      <strong className="event-model-label">
                        {t("Local AI observation", "Наблюдение локального ИИ")}
                      </strong>
                    )}
                    <p>{t(e.message)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        <aside className="research-aside">
          <div className="aside-card">
            <div className="aside-title">
              <ListFilter size={17} />
              <h3>{t("Параметры поиска")}</h3>
            </div>
            <div className="budget-meter">
              <div>
                <span>{t("Время")}</span>
                <strong>
                  {duration(elapsed)} / {job.brief.budget.minutes} {t("мин")}
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
                <dt>{t("Запросы")}</dt>
                <dd>
                  {job.stats.queries} / {job.brief.budget.queries}
                </dd>
              </div>
              <div>
                <dt>{t("Страницы, включая ошибки")}</dt>
                <dd>
                  {job.stats.pages} / {job.brief.budget.pages}
                </dd>
              </div>
              <div>
                <dt>{t("Этапы планирования")}</dt>
                <dd>
                  {job.rounds} / {job.brief.budget.rounds}
                </dd>
              </div>
              <div>
                <dt>{t("Языки")}</dt>
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
              {t("Изменить бюджет")}
            </button>
            {running && (
              <small className="small-muted">
                {t("Для изменения параметров поставьте поиск на паузу.")}
              </small>
            )}
          </div>
          <div className="aside-card">
            <div className="aside-title">
              <Target size={17} />
              <h3>{t("Ваши ориентиры")}</h3>
            </div>
            <button
              className="button secondary full"
              disabled={running || pending}
              onClick={() => {
                setRefining(true);
                setContinueOpen(true);
              }}
            >
              {t("Refine & continue", "Уточнить и продолжить")}
            </button>
            {!!job.brief.evidence_clues?.length && (
              <p className="small-muted">
                {job.brief.evidence_clues.map((c) => c.text).join(" · ")}
              </p>
            )}
            <p className="context-text">
              {job.brief.context || t("Дополнительные сведения не указаны.")}
            </p>
            {job.brief.aliases.length > 0 && (
              <p className="small-muted">
                {t("Варианты:")}
                {job.brief.aliases.join(", ")}
              </p>
            )}
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                if (await refine(note)) setNote("");
              }}
            >
              <label className="sr-only" htmlFor="refinement">
                {t("Новое уточнение")}
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
                    ? t("Приостановите поиск, чтобы добавить сведения")
                    : t("Добавьте новое уточнение…")
                }
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
              <button
                disabled={running || note.trim().length < 2 || pending}
                className="button text full"
              >
                <Plus size={15} />
                {t("Добавить ориентир")}
              </button>
            </form>
          </div>
          <div className="local-footnote">
            <Cpu size={19} />
            <div>
              <strong>{t("Только локальный ИИ")}</strong>
              <p>
                {job.settings_snapshot.model ||
                  t("Модель будет выбрана при запуске")}
              </p>
            </div>
          </div>
          <button className="delete-button" onClick={remove} disabled={running}>
            <Trash2 size={14} />
            {t("Удалить исследование")}
          </button>
        </aside>
      </div>
    </div>
  );
}
