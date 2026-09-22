import { useState } from "react";
import type { Brief, Budget, Detail } from "../types";
import { t } from "../i18n";
import { languages, split } from "../constants";
import { Modal, Field, BudgetFields } from "./ui";
import ClueFields from "./ClueFields";
export type Continuation = {
  brief: Brief;
  additional_budget: Budget;
  start: boolean;
};
export default function ContinueDialog({
  job,
  close,
  save,
  pending,
  error,
  refining = true,
}: {
  job: Detail;
  close: () => void;
  save: (v: Continuation) => Promise<boolean>;
  pending: boolean;
  error: string;
  refining?: boolean;
}) {
  const [brief, setBrief] = useState<Brief>(structuredClone(job.brief));
  const [budget, setBudget] = useState<Budget>({
    minutes: 30,
    queries: 40,
    pages: 80,
    rounds: 5,
  });
  const [start, setStart] = useState(!refining);
  const [editCriteria, setEditCriteria] = useState(refining);
  const set = <K extends keyof Brief>(key: K, value: Brief[K]) =>
    setBrief((b) => ({ ...b, [key]: value }));
  return (
    <Modal
      title={
        editCriteria
          ? t("Refine & continue", "Уточнить и продолжить")
          : t("Continue search", "Продолжить поиск")
      }
      subtitle={t(
        "Continue the saved work, then explore new directions. Your findings stay in this project.",
        "Продолжим сохранённую работу, затем новые направления. Находки остаются в этом проекте.",
      )}
      close={close}
    >
      <form
        className="continuation-form"
        onSubmit={async (e) => {
          e.preventDefault();
          if (await save({ brief, additional_budget: budget, start })) close();
        }}
      >
        {error && (
          <p role="alert" className="source-error">
            {error}
          </p>
        )}
        <div className="continuation-summary">
          <strong>{job.name}</strong>
          <p>
            {[job.brief.city, job.brief.country].filter(Boolean).join(" · ")}
          </p>
          {job.reason && <p>{t(job.reason)}</p>}
          <p>
            {job.continuation?.pending_steps || 0}{" "}
            {t("saved steps waiting", "сохранённых шагов в очереди")}
          </p>
        </div>
        <label className="check-row">
          <input
            type="checkbox"
            checked={editCriteria}
            onChange={(e) => {
              setEditCriteria(e.target.checked);
              if (!e.target.checked) setBrief(structuredClone(job.brief));
            }}
          />
          {t(
            "Change criteria or add clues",
            "Изменить условия или добавить ориентиры",
          )}
        </label>
        {editCriteria && (
          <>
            <Field label={t("Name", "Имя")}>
              {(id) => (
                <input
                  id={id}
                  required
                  minLength={2}
                  maxLength={160}
                  value={brief.name}
                  onChange={(e) => set("name", e.target.value)}
                />
              )}
            </Field>
            <Field label={t("Known name variants", "Известные варианты имени")}>
              {(id) => (
                <input
                  id={id}
                  defaultValue={brief.aliases.join(", ")}
                  onChange={(e) => set("aliases", split(e.target.value))}
                />
              )}
            </Field>
            <Field
              label={t("Context and new clues", "Контекст и новые ориентиры")}
            >
              {(id) => (
                <textarea
                  id={id}
                  rows={4}
                  maxLength={6000}
                  value={brief.context}
                  onChange={(e) => set("context", e.target.value)}
                />
              )}
            </Field>
            <ClueFields
              value={brief.evidence_clues || []}
              onChange={(v) => set("evidence_clues", v)}
            />
            <details className="continuation-filters">
              <summary>
                {t(
                  "Languages, names and source filters",
                  "Языки, имена и фильтры источников",
                )}
              </summary>
              <div className="grid two">
                <Field
                  label={t("City", "Город")}
                  hint={t(
                    "Required biographical connection, including the past",
                    "Обязательная биографическая связь, включая прошлое",
                  )}
                >
                  {(id) => (
                    <input
                      id={id}
                      maxLength={120}
                      value={brief.city}
                      onChange={(e) => set("city", e.target.value)}
                    />
                  )}
                </Field>
                <Field label={t("Country", "Страна")}>
                  {(id) => (
                    <input
                      id={id}
                      maxLength={120}
                      value={brief.country}
                      onChange={(e) => set("country", e.target.value)}
                    />
                  )}
                </Field>
              </div>
              <div className="grid two">
                {(["year_from", "year_to"] as const).map((key) => (
                  <Field
                    key={key}
                    label={
                      key === "year_from"
                        ? t("Birth year — from", "Год рождения — от")
                        : t("Birth year — to", "Год рождения — до")
                    }
                  >
                    {(id) => (
                      <input
                        id={id}
                        type="number"
                        min={1850}
                        max={2100}
                        value={brief[key] ?? ""}
                        onChange={(e) =>
                          set(key, e.target.value ? +e.target.value : null)
                        }
                      />
                    )}
                  </Field>
                ))}
              </div>
              <Field label={t("Previous names", "Прежние имена")}>
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
              <label className="check-row">
                <input
                  type="checkbox"
                  checked={brief.expand_names}
                  onChange={(e) => set("expand_names", e.target.checked)}
                />
                {t("Explore spelling variants", "Искать варианты написания")}
              </label>
              <Field label={t("Surname change", "Смена фамилии")}>
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
                    <option value="unknown">
                      {t("Unknown", "Неизвестно")}
                    </option>
                    <option value="possible">
                      {t("Possible", "Возможна")}
                    </option>
                    <option value="known">{t("Known", "Известна")}</option>
                  </select>
                )}
              </Field>
              <div className="language-options">
                {languages.map(([code, label]) => (
                  <label key={code}>
                    <input
                      type="checkbox"
                      checked={brief.languages.includes(code)}
                      onChange={(e) =>
                        set(
                          "languages",
                          e.target.checked
                            ? [...brief.languages, code]
                            : brief.languages.filter((l) => l !== code),
                        )
                      }
                    />
                    {label}
                  </label>
                ))}
              </div>
              <Field label={t("Include domains", "Искать только на доменах")}>
                {(id) => (
                  <input
                    id={id}
                    defaultValue={brief.include_domains.join(", ")}
                    placeholder="university.edu, example.org"
                    onChange={(e) =>
                      set("include_domains", split(e.target.value))
                    }
                  />
                )}
              </Field>
              <Field label={t("Exclude domains", "Исключить домены")}>
                {(id) => (
                  <input
                    id={id}
                    defaultValue={brief.exclude_domains.join(", ")}
                    onChange={(e) =>
                      set("exclude_domains", split(e.target.value))
                    }
                  />
                )}
              </Field>
              <Field
                label={t(
                  "Starting URLs, one per line",
                  "Исходные ссылки, по одной на строку",
                )}
              >
                {(id) => (
                  <textarea
                    id={id}
                    rows={3}
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
              <Field label={t("Search freshness", "Давность результатов")}>
                {(id) => (
                  <select
                    id={id}
                    value={brief.freshness}
                    onChange={(e) => set("freshness", e.target.value)}
                  >
                    {[
                      ["all", t("Any time", "За всё время")],
                      ["d", t("Day", "День")],
                      ["w", t("Week", "Неделя")],
                      ["m", t("Month", "Месяц")],
                      ["y", t("Year", "Год")],
                    ].map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                )}
              </Field>
            </details>
          </>
        )}
        <h3>{t("Allowance for the next pass", "Лимиты следующего прохода")}</h3>
        <BudgetFields value={budget} onChange={setBudget} />
        <p className="small-muted">
          {t(
            "These limits count from the work already done; they replace the unused allowance. Search stops when a limit is reached or no useful new direction remains. Previously visited URLs and completed queries are not repeated with unchanged criteria. Pending steps are finished first.",
            "Эти лимиты отсчитываются от уже выполненной работы и заменяют неиспользованный остаток. Поиск остановится при достижении лимита или отсутствии новых направлений. При прежних условиях прочитанные страницы и выполненные запросы не повторяются. Сначала завершаются сохранённые шаги.",
          )}
        </p>
        {editCriteria && (
          <p className="small-muted">
            {t(
              "Changing criteria creates a new revision and rechecks earlier findings. Keeping them unchanged preserves reviews and the queue.",
              "Изменение условий создаёт новую версию и требует перепроверки находок. Если условия прежние, оценки и очередь сохраняются.",
            )}
          </p>
        )}
        <label className="check-row">
          <input
            type="checkbox"
            checked={start}
            onChange={(e) => setStart(e.target.checked)}
          />
          {t(
            "Start the local search after saving",
            "Запустить локальный поиск после сохранения",
          )}
        </label>
        <button
          className="button primary full"
          disabled={pending || !brief.languages.length}
        >
          {pending
            ? t("Saving…", "Сохраняем…")
            : start
              ? t("Save & continue search", "Сохранить и продолжить поиск")
              : editCriteria
                ? t("Save new criteria", "Сохранить новые критерии")
                : t("Save allowance", "Сохранить лимиты")}
        </button>
      </form>
    </Modal>
  );
}
