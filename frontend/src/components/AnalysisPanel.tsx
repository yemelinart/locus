import { useEffect, useState } from "react";
import type { Analysis, Detail } from "../types";
import { api } from "../api";
import { t } from "../i18n";
import { duration } from "../constants";
export default function AnalysisPanel({ job }: { job: Detail }) {
  const [value, setValue] = useState<Analysis | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    let alive = true;
    api<Analysis>(`/jobs/${job.id}/analysis`)
      .then((a) => {
        if (alive) setValue(a);
      })
      .catch((e) => {
        if (alive) setError(e.message);
      });
    return () => {
      alive = false;
    };
  }, [job.id, job.updated_at]);
  if (error) return <p role="alert">{t(error)}</p>;
  if (!value) return <p>{t("Loading analysis…", "Загрузка анализа…")}</p>;
  return (
    <section className="analysis-panel">
      <h2>{t("Research at a glance", "Исследование в деталях")}</h2>
      <p className="small-muted">
        {t(
          "Computed from recorded activity. No extra AI call. Candidate cards are not a count of unique people.",
          "На основе записанных действий, без дополнительного вызова ИИ. Число карточек не равно числу уникальных людей.",
        )}
      </p>
      <div className="analysis-stats">
        {[
          [t("Active time", "Активное время"), duration(job.active_seconds)],
          [t("Quoted claims", "Утверждений с цитатами"), value.facts],
          [t("Confirmed by you", "Подтверждено вами"), value.confirmed],
          [t("Unavailable pages", "Недоступных страниц"), value.failed_sources],
        ].map(([label, v]) => (
          <div key={label}>
            <strong>{v}</strong>
            <span>{label}</span>
          </div>
        ))}
      </div>
      <h3>
        {t(
          "Search engines actually queried",
          "Реальные обращения к поисковикам",
        )}
      </h3>
      {!value.engine_coverage_known ? (
        <p className="notice">
          {t(
            "This earlier research has no per-engine audit. Enabled engines cannot be presented as engines actually queried.",
            "В этом раннем исследовании нет журнала по системам. Включённые поисковики нельзя считать фактически опрошенными.",
          )}
        </p>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                {[
                  t("Engine", "Система"),
                  t("Attempts", "Попытки"),
                  t("Results", "Результаты"),
                  t("Errors", "Ошибки"),
                  t("Time", "Время"),
                ].map((v) => (
                  <th key={v}>{v}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {value.engines.map((e) => (
                <tr key={e.engine}>
                  <td>{e.engine}</td>
                  <td>{e.attempts}</td>
                  <td>{e.results}</td>
                  <td>{e.failed}</td>
                  <td>{duration(e.seconds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <h3>{t("Websites inspected", "Проверенные сайты")}</h3>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {[
                t("Website", "Сайт"),
                t("Read", "Прочитано"),
                t("Unavailable", "Недоступно"),
                t("Claims", "Утверждения"),
              ].map((v) => (
                <th key={v}>{v}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {value.domains.map((d) => (
              <tr key={d.domain}>
                <td>{d.domain}</td>
                <td>{d.read}</td>
                <td>{d.unavailable}</td>
                <td>{d.facts}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3>{t("Matching clues", "Совпадающие ориентиры")}</h3>
      <p className="small-muted">
        {t(
          "Model suggestions to review; these do not establish identity.",
          "Предложения модели для проверки; они не устанавливают личность.",
        )}
      </p>
      {value.clues.length ? (
        <ul>
          {value.clues.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      ) : (
        <p>{t("No clues recorded yet.", "Ориентиров пока нет.")}</p>
      )}
      <h3>
        {t("Contradictions & next steps", "Противоречия и следующие шаги")}
      </h3>
      {value.contradictions.length > 0 && (
        <ul>
          {value.contradictions.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      )}
      <ul>
        {value.unreviewed > 0 && (
          <li>
            {t(
              "Review unconfirmed candidate cards against your known context.",
              "Сопоставьте непроверенные карточки с известными вам сведениями.",
            )}
          </li>
        )}
        {value.failed_sources > 0 && (
          <li>
            {t(
              "Check unavailable sources before concluding that no information exists.",
              "Проверьте недоступные источники перед выводом об отсутствии информации.",
            )}
          </li>
        )}
        {value.pending_queries > 0 && (
          <li>
            {t(
              "Pending queries remain. Extend the relevant budget to continue.",
              "В очереди остались запросы. Расширьте соответствующий бюджет для продолжения.",
            )}
          </li>
        )}
        <li>
          {t(
            "Add a known name variant, school, organisation or public project to make the next round more specific.",
            "Добавьте известный вариант имени, место учёбы, организацию или публичный проект для уточнения следующего этапа.",
          )}
        </li>
      </ul>
    </section>
  );
}
