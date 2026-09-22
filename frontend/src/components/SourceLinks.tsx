import type { Detail, LinkDecision } from "../types";
import { t } from "../i18n";

export default function SourceLinks({
  job,
  review,
  disabled,
}: {
  job: Detail;
  review: (decision: LinkDecision) => void;
  disabled: boolean;
}) {
  const links = job.linkage;
  if (!links?.proposals.length) return null;
  const candidate = (id: string) => job.candidates.find((c) => c.id === id)!;
  const source = (id: string) => job.sources.find((s) => s.id === id)!;
  const state = (s: string) =>
    s === "eligible"
      ? t(
          "All required criteria supported",
          "Все обязательные критерии подтверждены",
        )
      : s === "conflicting"
        ? t(
            "Conflicting evidence — review needed",
            "Противоречивые сведения — нужна проверка",
          )
        : s === "no_constraints"
          ? t(
              "No matching criteria supplied",
              "Критерии сопоставления не заданы",
            )
          : t(
              "Some required criteria remain unknown",
              "Часть обязательных критериев не подтверждена",
            );
  return (
    <section
      className="source-links"
      aria-label={t("Evidence across sources", "Сопоставление источников")}
    >
      <h2>{t("Evidence across sources", "Сопоставление источников")}</h2>
      <p className="small-muted">
        {t(
          "These pages contain actual links between them. A link is a lead, not proof of identity. Combine evidence only after checking that both records describe the same person. Original cards stay separate.",
          "Между страницами найдены реальные ссылки. Ссылка — зацепка, а не доказательство личности. Объединяйте свидетельства, только проверив, что обе записи относятся к одному человеку. Исходные карточки сохраняются отдельно.",
        )}
      </p>
      {links.groups.map((g) => (
        <article className="linked-profile" key={g.id}>
          <h3>
            {candidate(g.candidate_ids[0]).value.name} ·{" "}
            {state(g.identity_status)}
          </h3>
          <p className="small-muted">
            {t(
              "You confirmed these records describe the same person",
              "Вы подтвердили, что записи относятся к одному человеку",
            )}
            . {t("Sources", "Источники")}: {g.source_count}.{" "}
            {t("Source families", "Группы источников")}: {g.source_families}.
          </p>
          {g.identity_checks.map((check) => (
            <div className="linked-criterion" key={check.field}>
              <strong>
                {check.requested} ·{" "}
                {check.relation === "supports"
                  ? t("Supported", "Подтверждено")
                  : check.relation === "contradicts"
                    ? t("Contradiction", "Противоречие")
                    : t("Unknown", "Неизвестно")}
              </strong>
              {check.evidence.map((e, i) => (
                <div key={i}>
                  <blockquote>{e.quote}</blockquote>
                  <a
                    href={source(e.source_id).url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {source(e.source_id).title || source(e.source_id).url}
                  </a>
                </div>
              ))}
            </div>
          ))}
          {g.identity_status === "eligible" && (
            <details>
              <summary>
                {t(
                  "Public work and education · quoted sources",
                  "Деятельность и образование · цитаты источников",
                )}
              </summary>
              {g.candidate_ids.map((id) => (
                <div key={id}>
                  {candidate(id).assessment?.checked_facts.map((f) => (
                    <div key={f.index}>
                      <p>{f.statement}</p>
                      <blockquote>{f.quote}</blockquote>
                      <a
                        href={source(candidate(id).source_id).url}
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
        </article>
      ))}
      <details open={!links.groups.length}>
        <summary>
          {t("Review source links", "Проверить связи источников")} (
          {links.proposals.length})
        </summary>
        {links.proposals.map((p) => (
          <article
            className="source-link-proposal"
            key={p.left_id + p.right_id}
          >
            <h3>
              {candidate(p.left_id).value.name} ↔{" "}
              {candidate(p.right_id).value.name}
            </h3>
            <div>
              {[p.from_source, p.to_source].map((id) => (
                <p key={id}>
                  <a href={source(id).url} target="_blank" rel="noreferrer">
                    {source(id).title || source(id).url}
                  </a>
                </p>
              ))}
            </div>
            <blockquote>{p.context}</blockquote>
            <p className="small-muted">
              {p.kind === "profile_navigation"
                ? t(
                    "Named page heading and a link to its biography or public work; review the relationship.",
                    "Заголовок страницы с именем и ссылка на биографию или работы; проверьте связь.",
                  )
                : p.kind === "declared_same_as"
                  ? t(
                      "The page declares a profile link in its metadata; this can be wrong.",
                      "Страница заявляет связь с профилем в метаданных; она может быть ошибочной.",
                    )
                  : t(
                      "Link context copied from the source page.",
                      "Контекст ссылки взят со страницы источника.",
                    )}
            </p>
            {p.stale && (
              <p>
                {t(
                  "Criteria changed. Review this link again.",
                  "Критерии изменились. Проверьте связь заново.",
                )}
              </p>
            )}
            <div className="source-link-actions">
              <button
                className="button secondary"
                disabled={disabled || p.status === "confirmed"}
                onClick={() =>
                  review({
                    left_id: p.left_id,
                    right_id: p.right_id,
                    status: "confirmed",
                  })
                }
              >
                {p.status === "confirmed"
                  ? t("Link confirmed by you", "Связь подтверждена вами")
                  : t(
                      "Same person · combine evidence",
                      "Один человек · сопоставить сведения",
                    )}
              </button>
              <button
                className="button secondary"
                disabled={disabled || p.status === "rejected"}
                onClick={() =>
                  review({
                    left_id: p.left_id,
                    right_id: p.right_id,
                    status: "rejected",
                  })
                }
              >
                {p.status === "rejected"
                  ? t("Link rejected", "Связь отклонена")
                  : t("Different people", "Разные люди")}
              </button>
              {p.status !== "unreviewed" && (
                <button
                  className="button text"
                  disabled={disabled}
                  onClick={() =>
                    review({
                      left_id: p.left_id,
                      right_id: p.right_id,
                      status: "unreviewed",
                    })
                  }
                >
                  {t("Undo decision", "Отменить решение")}
                </button>
              )}
            </div>
          </article>
        ))}
      </details>
      {disabled && (
        <p className="small-muted">
          {t(
            "Pause research to review links.",
            "Для оценки связей приостановите поиск.",
          )}
        </p>
      )}
    </section>
  );
}
