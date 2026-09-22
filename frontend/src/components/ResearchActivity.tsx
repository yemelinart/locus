import { useState } from "react";
import {
  AudioLines,
  Cpu,
  ExternalLink,
  Pause,
  Play,
  Sparkles,
} from "lucide-react";
import type { Detail } from "../types";
import { t } from "../i18n";
import { host } from "../constants";
export default function ResearchActivity({ job }: { job: Detail }) {
  const [motion, setMotion] = useState(true);
  if (job.status === "draft") return null;
  const active = job.status === "running";
  const phase = active ? job.activity?.phase || "preparing" : job.status;
  const titles: Record<string, string> = {
    preparing: t("Preparing research", "Подготовка исследования"),
    planning: t(
      "Choosing the next direction",
      "Выбираем следующее направление",
    ),
    searching: t("Searching public indexes", "Ищем в публичных индексах"),
    reading: t("Reading a source", "Читаем источник"),
    extracting: t(
      "Reading the person's public background",
      "Разбираем сведения о человеке",
    ),
    verifying: t(
      "Checking the meaning and the match",
      "Проверяем смысл и совпадение",
    ),
    summarizing: t(
      "Checking the profile summary",
      "Проверяем краткое описание",
    ),
    queued: t("Waiting to start", "Ожидаем запуска"),
    paused: t("Research paused", "Исследование на паузе"),
    completed: t("This search pass has ended", "Этот проход поиска завершён"),
  };
  const stages = [
    "planning",
    "searching",
    "reading",
    "extracting",
    "verifying",
  ];
  const sites = [
    ...new Set(
      [job.activity?.url || "", ...job.sources.map((s) => s.url)]
        .filter(Boolean)
        .map(host),
    ),
  ].slice(0, 4);
  const notes = job.candidates
    .filter(
      (c) =>
        c.assessment?.model_reviewed &&
        c.assessment.note &&
        !c.assessment.excluded &&
        !["unresolved", "conflicting"].includes(
          c.assessment.identity_status || "",
        ) &&
        c.status !== "rejected",
    )
    .sort((a, b) =>
      (b.verification?.at || "").localeCompare(a.verification?.at || ""),
    );
  const note = notes[0];
  const source = note && job.sources.find((s) => s.id === note.source_id);
  const target = active ? job.activity?.target : job.reason;
  const aiPhase = [
    "planning",
    "extracting",
    "verifying",
    "summarizing",
  ].includes(phase);
  const explanations: Record<string, string> = {
    planning: t(
      "Local AI compares the clues, previous queries and reviewed findings to choose new directions.",
      "Локальный ИИ сопоставляет ориентиры, выполненные запросы и проверенные находки, чтобы выбрать новые направления.",
    ),
    searching: t(
      "The search adapter requests public results. A matching name in the results is only a lead.",
      "Поисковый модуль запрашивает публичную выдачу. Совпадение имени в ней — пока только зацепка.",
    ),
    reading: t(
      "The reader opens a public page. Already visited URLs are skipped; an inaccessible page is not a negative match.",
      "Модуль чтения открывает публичную страницу. Посещённые адреса пропускаются; недоступная страница не означает, что человек не подходит.",
    ),
    extracting: t(
      "Local AI identifies the person and public work or education described on this page. Attribution is checked next.",
      "Локальный ИИ выделяет сведения о человеке, его публичной работе и образовании. Затем проверяется, кому эти сведения относятся.",
    ),
    verifying: t(
      "Local AI checks whether the page describes the requested person. The engine validates the name, places and dates. Missing links stay unconfirmed.",
      "Локальный ИИ проверяет, о нужном ли человеке написано. Движок проверяет имя, места и даты. Отсутствующая связь остаётся неподтверждённой.",
    ),
    summarizing: t(
      "The identity check has been saved. Local AI checks the optional short description against reviewed facts.",
      "Проверка совпадения уже сохранена. Локальный ИИ сверяет необязательное краткое описание с проверенными фактами.",
    ),
  };
  const latest = job.candidates
    .filter(
      (c) =>
        c.assessment?.model_reviewed &&
        !c.assessment.excluded &&
        c.status !== "rejected",
    )
    .sort((a, b) =>
      (b.verification?.at || "").localeCompare(a.verification?.at || ""),
    )[0];
  const latestSource =
    latest && job.sources.find((s) => s.id === latest.source_id);
  const eligibleRecords = job.candidates.filter(
    (c) =>
      c.assessment?.identity_status === "eligible" &&
      !c.assessment.excluded &&
      c.status !== "rejected",
  ).length;
  const relationLabel = (relation: string) =>
    relation === "supports"
      ? t("Supported", "Подтверждено источником")
      : relation === "contradicts"
        ? t("Conflict", "Противоречие")
        : t("Not established", "Связь не установлена");
  const fieldLabel = (field: string) =>
    ({
      city: t("City", "Город"),
      country: t("Country", "Страна"),
      birth_year: t("Birth year", "Год рождения"),
    })[field] || t("Clue", "Ориентир");
  return (
    <section
      className={`research-activity ${active && motion ? "animating" : "still"}`}
      data-phase={phase}
      aria-label={t("Live research activity", "Ход исследования")}
    >
      <div className="activity-visual" aria-hidden="true">
        <div className="activity-orbit orbit-a" />
        <div className="activity-orbit orbit-b" />
        <div className="activity-orbit orbit-c" />
        <svg className="activity-network" viewBox="0 0 300 240">
          <g>
            {sites.map((siteHost, i) => (
              <path
                className={
                  job.activity?.url &&
                  siteHost === host(job.activity.url) &&
                  ["reading", "extracting", "verifying"].includes(phase)
                    ? "active"
                    : ""
                }
                key={i}
                d={
                  [
                    "M150 120 Q90 30 32 42",
                    "M150 120 Q205 20 270 48",
                    "M150 120 Q70 205 35 194",
                    "M150 120 Q235 210 268 194",
                  ][i]
                }
              />
            ))}
          </g>
        </svg>
        <div className="activity-core">
          <Cpu size={29} strokeWidth={1.3} />
          <span>LOCUS</span>
        </div>
        {sites.map((site, i) => (
          <div
            className={`activity-site site-${i} ${job.sources.find((s) => host(s.url) === site)?.status || "pending"}`}
            key={site}
          >
            <span />
            {site}
          </div>
        ))}
        <span className="activity-visual-caption">
          {t("LOCAL RESEARCH", "ЛОКАЛЬНОЕ ИССЛЕДОВАНИЕ")}
        </span>
      </div>
      <div className="activity-content">
        <div className="activity-topline">
          <span className="eyebrow">
            <AudioLines size={13} />
            {active
              ? t("WORKING NOW", "СЕЙЧАС В РАБОТЕ")
              : t("SEARCH STATE", "СОСТОЯНИЕ ПОИСКА")}
          </span>
          <button
            className="icon-button"
            aria-label={
              motion
                ? t("Pause animation", "Остановить анимацию")
                : t("Enable animation", "Включить анимацию")
            }
            aria-pressed={motion}
            onClick={() => setMotion(!motion)}
          >
            {motion ? <Pause size={14} /> : <Play size={14} />}
          </button>
        </div>
        <h2 aria-live="polite">{titles[phase] || phase}</h2>
        {active && (
          <p className="activity-actor">
            <strong>
              {aiPhase
                ? t("LOCAL AI", "ЛОКАЛЬНЫЙ ИИ")
                : t("WEB MODULE", "ВЕБ-МОДУЛЬ")}
            </strong>
            {aiPhase && <span>{job.settings_snapshot.model}</span>}
          </p>
        )}
        {target && <p className="activity-target">{t(target)}</p>}
        {active && explanations[phase] && (
          <p className="activity-explanation">{explanations[phase]}</p>
        )}
        {active && job.activity?.url && (
          <a
            className="activity-source"
            href={job.activity.url}
            target="_blank"
            rel="noreferrer"
          >
            {host(job.activity.url)}
            <ExternalLink size={12} />
          </a>
        )}
        <div
          className="activity-stages"
          aria-label={t("Current processing stage", "Текущий этап обработки")}
        >
          {stages.map((stage, i) => (
            <span
              key={stage}
              className={
                (phase === "summarizing" ? "verifying" : phase) === stage
                  ? "current"
                  : ""
              }
              aria-current={
                (phase === "summarizing" ? "verifying" : phase) === stage
                  ? "step"
                  : undefined
              }
            >
              <b>{i + 1}</b>
              {
                [
                  t("Plan", "План"),
                  t("Search", "Поиск"),
                  t("Read", "Чтение"),
                  t("Understand", "Разбор"),
                  t("Review", "Проверка"),
                ][i]
              }
            </span>
          ))}
        </div>
        <p className="activity-footnote">
          {t(
            "Current stage and sources encountered during this research.",
            "Текущий этап и источники, встреченные в этом исследовании.",
          )}
        </p>
        {job.queue && (
          <p className="activity-queue">
            {t("Saved queue", "Сохранённая очередь")}: {job.queue.search}{" "}
            {t("queries", "запросов")} · {job.queue.fetch}{" "}
            {t("pages", "страниц")} · {job.queue.analyze + job.queue.review}{" "}
            {t("AI checks", "проверок ИИ")}
          </p>
        )}
      </div>
      <div className="activity-findings">
        <div className="activity-counts">
          <span>
            <strong>{eligibleRecords}</strong>{" "}
            {t("meet the criteria", "соответствуют условиям")}
          </span>
          <span>
            <strong>{job.conclusion?.unresolved_identity || 0}</strong>{" "}
            {t("unconfirmed", "не подтверждены")}
          </span>
          <span>
            <strong>{job.conclusion?.conflicting_identity || 0}</strong>{" "}
            {t("conflicting", "с противоречиями")}
          </span>
        </div>
        <small>
          {t(
            "Counts refer to source records, not distinct people. A match still needs your review.",
            "Это количество записей из источников, а не отдельных людей. Совпадение ещё требует вашей проверки.",
          )}
        </small>
        {latest && (
          <details className="activity-verdict" open>
            <summary>
              {t("Latest identity check", "Последняя проверка совпадения")}:{" "}
              {latest.value.name}
            </summary>
            <p>
              {latest.assessment?.identity_status === "eligible"
                ? t(
                    "This record supports the required links. Check whether you recognise the person.",
                    "Эта запись подтверждает обязательные связи. Проверьте, узнаёте ли вы человека.",
                  )
                : latest.assessment?.identity_status === "conflicting"
                  ? t(
                      "This record conflicts with the search criteria and is kept separate.",
                      "Эта запись противоречит условиям поиска и остаётся отдельно.",
                    )
                  : latest.assessment?.identity_status === "no_constraints"
                    ? t(
                        "No additional identity criteria were provided. A name alone cannot establish the match.",
                        "Дополнительные условия не заданы. Одного имени недостаточно, чтобы установить совпадение.",
                      )
                    : t(
                        "The required links are not all established. This record is not an accepted match.",
                        "Не все обязательные связи установлены. Эта запись не считается найденным совпадением.",
                      )}
            </p>
            <ul>
              {latest.assessment?.identity_checks?.map((check) => (
                <li key={check.field}>
                  <span>
                    {fieldLabel(check.field)}:{" "}
                    <strong>{check.requested}</strong>
                  </span>
                  <span className={`relation-${check.relation}`}>
                    {relationLabel(check.relation)}
                  </span>
                </li>
              ))}
            </ul>
            {latestSource && (
              <a href={latestSource.url} target="_blank" rel="noreferrer">
                {host(latestSource.url)} <ExternalLink size={12} />
              </a>
            )}
          </details>
        )}
      </div>
      {note && (
        <div className="activity-note">
          <div>
            <Sparkles size={15} />
            <strong>
              {t(
                "Local AI · latest observation",
                "Локальный ИИ · последнее наблюдение",
              )}
            </strong>
          </div>
          <p>{note.assessment!.note}</p>
          <small>
            {t(
              "Model interpretation, review required. Claims: ",
              "Комментарий модели, требует проверки. Утверждения: ",
            )}
            {note.assessment!.note_facts.map((i) => i + 1).join(", ")}
            {source && (
              <>
                {" "}
                ·{" "}
                <a href={source.url} target="_blank" rel="noreferrer">
                  {host(source.url)}
                </a>
              </>
            )}
          </small>
        </div>
      )}
    </section>
  );
}
