import { useState } from "react";
import type { Detail } from "../types";
import { t } from "../i18n";

export default function DiscoveryLeads({ job }: { job: Detail }) {
  const [all, setAll] = useState(false);
  const leads = job.leads || [];
  if (!leads.length) return null;
  return (
    <section
      className="research-conclusion discovery-leads"
      aria-label={t("Discovered links", "Найденные ссылки")}
    >
      <h2>
        {t("Discovered links", "Найденные ссылки")} · {leads.length}
      </h2>
      <p>
        {t(
          "These pages mention a matching name. They are leads to review, not identified people. A blocked page remains available to open yourself; missing city evidence remains unknown.",
          "На этих страницах встречается подходящее имя. Это ссылки для проверки, личность ещё не установлена. Даже если сайт запретил автоматическое чтение, ссылку можно открыть самому; связь с городом остаётся неизвестной.",
        )}
      </p>
      <div className="discovery-grid">
        {(all ? leads : leads.slice(0, 4)).map((lead) => (
          <article key={lead.id} className="discovery-card">
            <a href={lead.url} target="_blank" rel="noreferrer">
              {lead.title}
            </a>
            <small>
              {new URL(lead.url).hostname} ·{" "}
              {lead.state === "unavailable"
                ? t(
                    "Automatic reading unavailable",
                    "Автоматическое чтение недоступно",
                  )
                : lead.state === "read"
                  ? t(
                      "Page read · identity needs review",
                      "Страница прочитана · личность требует проверки",
                    )
                  : t("Awaiting page review", "Ожидает проверки страницы")}
            </small>
            {lead.snippet && (
              <details>
                <summary>
                  {t(
                    "Search preview · unverified",
                    "Текст поисковой выдачи · не проверен",
                  )}
                </summary>
                <p>{lead.snippet}</p>
              </details>
            )}
            {lead.query && (
              <small>
                {t("Found with", "Найдено по запросу")}: {lead.query}
              </small>
            )}
          </article>
        ))}
      </div>
      {leads.length > 4 && (
        <button className="button secondary" onClick={() => setAll(!all)}>
          {all
            ? t("Show fewer", "Свернуть")
            : t("Show all discovered links", "Показать все найденные ссылки")}
        </button>
      )}
    </section>
  );
}
