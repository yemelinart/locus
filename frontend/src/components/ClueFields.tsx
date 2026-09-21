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
          "Add exact school, organization or work titles, one per line. These are your search clues, not verified facts. The evidence meter checks their presence in quotations.",
          "Укажите названия учебных заведений, организаций или работ, по одному на строку. Это ваши ориентиры, а не проверенные факты. Шкала проверяет их присутствие в цитатах.",
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
