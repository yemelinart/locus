import type { Candidate } from "../types";
import { t } from "../i18n";
export default function EvidenceMeter({
  assessment: a,
}: {
  assessment?: Candidate["assessment"];
}) {
  if (!a) return null;
  const labels: Record<string, string> = {
    insufficient: t("Insufficient evidence", "Недостаточно свидетельств"),
    limited: t("Limited support", "Слабая обоснованность"),
    supported: t("Supporting clues", "Есть подтверждающие ориентиры"),
    strong: t(
      "Multiple supporting clues",
      "Несколько подтверждающих ориентиров",
    ),
    conflicting: t("Needs conflict review", "Нужно проверить противоречия"),
    excluded: t("Archived by current filters", "В архиве по текущим фильтрам"),
  };
  const strength =
    {
      insufficient: 0,
      limited: 1,
      supported: 2,
      strong: 3,
      conflicting: 0,
      excluded: 0,
    }[a.level] ?? 0;
  return (
    <details className={`evidence-meter ${a.level}`}>
      <summary>
        <span className="evidence-bars" aria-hidden="true">
          {[1, 2, 3].map((n) => (
            <i key={n} className={n <= strength ? "filled" : ""} />
          ))}
        </span>
        <span>
          <strong>{labels[a.level]}</strong>
          <small>{t("Why this assessment?", "Почему такая оценка?")}</small>
        </span>
      </summary>
      <div className="evidence-explanation">
        <p>
          {t(
            "Evidence support, not an identity probability. Exact supplied names and structured clues in recorded quotes are counted. Spelling hypotheses, model opinions and missing information do not increase support.",
            "Обоснованность, а не вероятность личности. Учитываются заданные имена и структурированные ориентиры в записанных цитатах. Гипотезы написания, мнение модели и отсутствие сведений не усиливают оценку.",
          )}
        </p>
        {a.name_quote ? (
          <>
            <strong>
              {t("Name found in a quote", "Имя найдено в цитате")}
            </strong>
            <blockquote>{a.name_quote}</blockquote>
          </>
        ) : (
          <p>
            {t(
              "The supplied names are not present in the recorded quotes. Check spelling and the original page.",
              "Заданных имён нет в записанных цитатах. Проверьте написание и исходную страницу.",
            )}
          </p>
        )}
        {a.supported.map((c, i) => (
          <div key={i}>
            <strong>{c.text}</strong>
            <blockquote>{c.quote}</blockquote>
          </div>
        ))}
        {!!a.missing.length && (
          <p>
            {t(
              "Not found in these quotes (not a contradiction): ",
              "Не найдено в этих цитатах (это не противоречие): ",
            )}
            {a.missing.map((c) => c.text).join(" · ")}
          </p>
        )}
        {!!a.flags.length && (
          <p>
            {t(
              "Model flags require review: ",
              "Замечания модели требуют проверки: ",
            )}
            {a.flags.join(" · ")}
          </p>
        )}
        {a.excluded && (
          <p>
            {t(
              "The source falls outside the current domain filters. Its evidence is preserved. Change the filters to restore it.",
              "Источник не подходит под текущие фильтры доменов. Свидетельства сохранены. Измените фильтры, чтобы вернуть карточку.",
            )}
          </p>
        )}
        <p>
          {t(
            "Name alone: limited. Name + one clue type: supporting. Name + two clue types: multiple supporting clues. This does not establish that every quote describes the same person.",
            "Только имя — слабая обоснованность. Имя и один тип ориентиров — есть поддержка. Имя и два типа — несколько ориентиров. Это не доказывает, что все цитаты относятся к одному человеку.",
          )}
        </p>
      </div>
    </details>
  );
}
