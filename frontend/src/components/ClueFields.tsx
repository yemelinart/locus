import type { EvidenceClue } from "../types";
import { t } from "../i18n";
import { Field } from "./ui";
export default function ClueFields({
  value,
  onChange,
}: {
  value: EvidenceClue[];
  onChange: (v: EvidenceClue[]) => void;
}) {
  return (
    <div className="clue-fields">
      <h3>{t("Known public context", "Известный публичный контекст")}</h3>
      <p className="small-muted">
        {t(
          "Add known school, organization or work titles, one per line. Each becomes a required matching criterion: a source must support its connection to this person. Put uncertain suggestions in additional context instead.",
          "Укажите известные учебные заведения, организации или работы, по одному на строку. Каждый пункт — обязательный критерий: источник должен подтверждать его связь с этим человеком. Неуверенные предположения лучше записать в дополнительном контексте.",
        )}
      </p>
      {(
        [
          ["education", t("School or university", "Школа или университет")],
          [
            "organization",
            t("Organization or workplace", "Организация или место работы"),
          ],
          [
            "public_work",
            t("Publication or public work", "Публикация или публичная работа"),
          ],
        ] as const
      ).map(([kind, label]) => (
        <Field key={kind} label={label}>
          {(id) => (
            <textarea
              id={id}
              rows={2}
              defaultValue={value
                .filter((c) => c.kind === kind)
                .map((c) => c.text)
                .join("\n")}
              onChange={(e) =>
                onChange([
                  ...value.filter((c) => c.kind !== kind),
                  ...e.target.value
                    .split("\n")
                    .map((text) => text.trim())
                    .filter(Boolean)
                    .map((text) => ({ kind, text })),
                ])
              }
            />
          )}
        </Field>
      ))}
    </div>
  );
}
