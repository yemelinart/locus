import { CircleHelp, FileCheck2, ShieldQuestion } from "lucide-react";
import type { Detail } from "../types";
import { t } from "../i18n";
export default function ResearchConclusion({ job }: { job: Detail }) {
  const c = job.conclusion;
  if (!c || c.state === "not_started") return null;
  const confirmed = job.candidates.filter(
    (x) =>
      x.status === "confirmed" &&
      !x.assessment?.review_outdated &&
      !x.assessment?.excluded &&
      !["unresolved", "conflicting"].includes(
        x.assessment?.identity_status || "",
      ) &&
      x.assessment?.checked_facts?.length,
  );
  const titles: Record<string, string> = {
    no_accessible_sources: t(
      "No readable sources yet",
      "Прочитанных источников пока нет",
    ),
    no_supported_findings: t(
      "No supported match established",
      "Обоснованного совпадения пока нет",
    ),
    limited: t(
      "Some findings, identity still unclear",
      "Сведения найдены, личность пока не установлена",
    ),
    possible: t(
      "A promising match to review",
      "Есть совпадение, которое стоит проверить",
    ),
    multiple_candidates: t(
      "Several candidate cards need review",
      "Несколько карточек требуют проверки",
    ),
  };
  return (
    <section
      className={`research-conclusion ${c.state}`}
      aria-label={t("Research conclusion", "Вывод исследования")}
    >
      <div className="conclusion-heading">
        <ShieldQuestion size={21} />
        <div>
          <span className="eyebrow">
            {c.provisional
              ? t("INTERIM FINDINGS", "ПРОМЕЖУТОЧНЫЙ РЕЗУЛЬТАТ")
              : t("RESEARCH FINDINGS", "РЕЗУЛЬТАТ ИССЛЕДОВАНИЯ")}
          </span>
          <h2>{titles[c.state]}</h2>
        </div>
      </div>
      <p>
        {t(
          "This is what the checked sources support so far. Review the candidate cards before deciding whether they describe the person you mean. Missing information is not a contradiction.",
          "Это то, что пока поддерживают проверенные источники. Изучите карточки перед решением, относятся ли они к нужному человеку. Отсутствие сведений не означает противоречия.",
        )}
      </p>
      <div className="conclusion-counts">
        <span>
          <FileCheck2 size={15} />
          {t("Reviewed claims", "Утверждений после проверки")}:{" "}
          {c.reviewed_claims}
        </span>
        <span>
          {t("Pages read", "Страниц прочитано")}: {c.read_sources}
        </span>
        <span>
          {t("Unavailable", "Недоступно")}: {c.unavailable_sources}
        </span>
      </div>
      {!!job.retryable_model_steps && (
        <p className="conclusion-pending">
          {t(
            "AI steps left unverified after invalid responses",
            "Шагов ИИ осталось без проверки из-за неверных ответов",
          )}
          : {job.retryable_model_steps}.{" "}
          {t(
            "These are not negative findings. Continue to retry the saved steps.",
            "Это не отрицательный результат поиска. Продолжение повторит сохранённые шаги.",
          )}
        </p>
      )}
      {!!c.linked_matches && (
        <p>
          {t(
            "Matching profiles with evidence across linked sources",
            "Подходящих профилей со свидетельствами из связанных источников",
          )}
          : {c.linked_matches}.
        </p>
      )}
      {!!c.unresolved_identity && (
        <p>
          {t(
            "Cards without evidence for all required criteria",
            "Карточек без подтверждения всех обязательных критериев",
          )}
          : {c.unresolved_identity}.{" "}
          {t(
            "They are kept in Connection unverified, outside matching results.",
            "Они сохранены в списке «Связь не подтверждена», отдельно от подходящих результатов.",
          )}
        </p>
      )}
      {!!c.conflicting_identity && (
        <p>
          {t(
            "Cards conflicting with required criteria",
            "Карточек с противоречиями обязательным критериям",
          )}
          : {c.conflicting_identity}.
        </p>
      )}
      {c.pending_cards > 0 && (
        <p className="conclusion-pending">
          <CircleHelp size={15} />
          {t(
            "Cards awaiting semantic review",
            "Карточек в ожидании смысловой проверки",
          )}
          : {c.pending_cards}.{" "}
          {t(
            "Their claims are not included in the profile overview yet.",
            "Их утверждения пока не включены в обзор профиля.",
          )}
        </p>
      )}
      {c.conflicting_cards > 0 && (
        <p>
          {t(
            "Cards with potential contradictions to review",
            "Карточек с возможными противоречиями для проверки",
          )}
          : {c.conflicting_cards}.
        </p>
      )}
      {c.confirmed_cards > 0 && (
        <p>
          {t("Cards confirmed by you", "Карточек подтверждено вами")}:{" "}
          {c.confirmed_cards}.{" "}
          {t(
            "This records your decision, not the truth of every source claim.",
            "Это ваше решение, а не подтверждение истинности всех утверждений источника.",
          )}
        </p>
      )}
      {!job.brief.evidence_clues?.length &&
        !job.brief.city &&
        !job.brief.country &&
        !job.brief.year_from &&
        !job.brief.year_to && (
          <p className="conclusion-pending">
            <CircleHelp size={15} />
            {t(
              "For a stronger comparison, add a known school, organisation or public work in Refine & continue. A name and search location alone keep the evidence meter limited.",
              "Для более точного сравнения добавьте известное учебное заведение, организацию или публичную работу через «Уточнить и продолжить». Одного имени и места поиска недостаточно для высокой оценки по шкале.",
            )}
          </p>
        )}
      {confirmed.length > 0 && (
        <details className="confirmed-profile">
          <summary>
            {t(
              "Your confirmed profile · public work & education",
              "Подтверждённый вами профиль · деятельность и образование",
            )}
          </summary>
          <p>
            {t(
              "Only cards you confirmed under the current criteria are included. This is a sourced overview, not a complete life history.",
              "Включены только карточки, подтверждённые вами при текущих критериях. Это обзор по источникам, а не полная история жизни.",
            )}
          </p>
          {confirmed.map((candidate) => (
            <div key={candidate.id}>
              {candidate.assessment!.checked_facts.map((f) => (
                <div key={f.index}>
                  <p>{f.statement}</p>
                  <blockquote>{f.quote}</blockquote>
                  <a
                    href={
                      job.sources.find((s) => s.id === candidate.source_id)?.url
                    }
                    target="_blank"
                    rel="noreferrer"
                  >
                    {t("Original source", "Исходный источник")}
                  </a>
                </div>
              ))}
            </div>
          ))}
        </details>
      )}
    </section>
  );
}
