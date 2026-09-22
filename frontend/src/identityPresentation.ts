import type { Candidate } from "./types";
import { t } from "./i18n";

export function identityPresentation(a?: Candidate["assessment"]) {
  if (a?.excluded)
    return {
      label: t("Archived by current filters", "В архиве по текущим фильтрам"),
      strength: 0,
      accepted: false,
    };
  if (!a || !a.model_reviewed)
    return {
      label: t("Identity check pending", "Совпадение ещё не проверено"),
      strength: 0,
      accepted: false,
    };
  if (a.identity_status === "conflicting")
    return {
      label: t("Conflicts with criteria", "Противоречит условиям"),
      strength: 0,
      accepted: false,
    };
  if (
    a.identity_status === "unresolved" ||
    a.identity_status === "no_constraints"
  ) {
    if (!a.name_quote || a.name_compatible === false)
      return {
        label: t(
          "Person attribution unconfirmed",
          "Принадлежность сведений не установлена",
        ),
        strength: 0,
        accepted: false,
      };
    const supported = a.identity_checks?.some((c) => c.relation === "supports");
    return {
      label: supported
        ? t("Required links unconfirmed", "Обязательные связи не подтверждены")
        : t(
            "Name only · identity unconfirmed",
            "Только имя · личность не установлена",
          ),
      strength: 0,
      accepted: false,
    };
  }
  if (a.identity_status === "eligible")
    return {
      label: t(
        "Required criteria supported",
        "Обязательные условия подтверждены",
      ),
      strength: a.level === "strong" ? 3 : 2,
      accepted: true,
    };
  // Missing state from an older response is not a positive identity decision.
  return {
    label: t("Unverified lead", "Непроверенная зацепка"),
    strength: 0,
    accepted: false,
  };
}
