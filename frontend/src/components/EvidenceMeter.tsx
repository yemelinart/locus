import type { Candidate } from "../types";
import { t } from "../i18n";
import { identityPresentation } from "../identityPresentation";
export default function EvidenceMeter({
  assessment: a,
}: {
  assessment?: Candidate["assessment"];
}) {
  if (!a) return null;
  const { label, strength } = identityPresentation(a);
  return (
    <>
      {!!a.identity_checks?.length && (
        <div
          className="identity-criteria"
          aria-label={t(
            "Required identity criteria",
            "Обязательные критерии личности",
          )}
        >
          <strong>{t("Required criteria", "Обязательные критерии")}</strong>
          {a.identity_checks.map((c) => (
            <div key={c.field}>
              <p>
                <b>{c.requested}</b> ·{" "}
                {c.relation === "supports"
                  ? t("Supported by source", "Подтверждено источником")
                  : c.relation === "contradicts"
                    ? t("Contradiction", "Противоречие")
                    : t("Connection unverified", "Связь не подтверждена")}
              </p>
              {c.quote && <blockquote>{c.quote}</blockquote>}
            </div>
          ))}
          <small>
            {t(
              "Missing evidence is not a match. A different current city does not disprove an earlier connection.",
              "Отсутствие сведений не считается совпадением. Другой нынешний город не исключает прежней связи.",
            )}
          </small>
        </div>
      )}
      <details className={`evidence-meter ${a.level}`}>
        <summary>
          <span className="evidence-bars" aria-hidden="true">
            {[1, 2, 3].map((n) => (
              <i key={n} className={n <= strength ? "filled" : ""} />
            ))}
          </span>
          <span>
            <strong>{label}</strong>
            <small>{t("Why this assessment?", "Почему такая оценка?")}</small>
          </span>
        </summary>
        <div className="evidence-explanation">
          <p>
            {t(
              "Evidence support, not an identity probability. A separate local-model pass reviews what each quote says about this candidate. The review can still be wrong; it is not independent corroboration.",
              "Обоснованность, а не вероятность личности. Отдельный проход локальной модели проверяет, что цитата говорит именно об этом кандидате. Проверка тоже может ошибаться и не является независимым подтверждением.",
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
              "The name alone never fills the match indicator. All required identity criteria must be supported before it becomes positive. Two clue types on one page are not two independent sources.",
              "Одно имя не заполняет шкалу совпадения. Для положительной оценки нужны подтверждения всех обязательных условий. Два типа ориентиров на одной странице — не два независимых источника.",
            )}
          </p>
        </div>
      </details>
    </>
  );
}
