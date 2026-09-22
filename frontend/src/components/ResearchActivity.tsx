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
    extracting: t("Finding source quotations", "Находим цитаты в источнике"),
    verifying: t(
      "Checking the meaning and the match",
      "Проверяем смысл и совпадение",
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
        {target && <p className="activity-target">{t(target)}</p>}
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
              className={phase === stage ? "current" : ""}
              aria-current={phase === stage ? "step" : undefined}
            >
              <b>{i + 1}</b>
              {
                [
                  t("Plan", "План"),
                  t("Search", "Поиск"),
                  t("Read", "Чтение"),
                  t("Extract", "Цитаты"),
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
