import { useSyncExternalStore } from "react";
import messages from "../../backend/locus/assets/messages.json";
export type Preferences = {
  language: "en" | "ru";
  palette: "forest" | "ocean" | "sand" | "graphite";
  tone: "light" | "soft" | "dark";
};
const defaults: Preferences = {
  language: "en",
  palette: "forest",
  tone: "light",
};
function load(): Preferences {
  try {
    const p = JSON.parse(localStorage.getItem("locus-preferences") || "{}");
    return {
      language: p.language === "ru" ? "ru" : "en",
      palette: ["forest", "ocean", "sand", "graphite"].includes(p.palette)
        ? p.palette
        : "forest",
      tone: ["light", "soft", "dark"].includes(p.tone) ? p.tone : "light",
    };
  } catch {
    return defaults;
  }
}
let prefs = load();
function apply() {
  document.documentElement.lang = prefs.language;
  document.title =
    prefs.language === "ru"
      ? "Locus — локальный поиск"
      : "Locus — local research";
  document.documentElement.dataset.palette = prefs.palette;
  document.documentElement.dataset.tone = prefs.tone;
  document.documentElement.style.colorScheme =
    prefs.tone === "dark" ? "dark" : "light";
}
apply();
export const getPreferences = () => prefs;
const listeners = new Set<() => void>();
export function setPreferences(p: Partial<Preferences>) {
  prefs = { ...prefs, ...p };
  try {
    localStorage.setItem("locus-preferences", JSON.stringify(prefs));
  } catch {}
  apply();
  listeners.forEach((fn) => fn());
}
export function usePreferences() {
  return useSyncExternalStore(
    (fn) => {
      listeners.add(fn);
      return () => {
        listeners.delete(fn);
      };
    },
    () => prefs,
  );
}
const reverse = Object.fromEntries(
  Object.entries(messages).map(([ru, en]) => [en, ru]),
);
const patterns: [RegExp, string][] = [
  [
    /^Критерии сохранены: версия (\d+). Прежние находки сохранены, обоснованность пересчитана.$/,
    "Criteria saved: revision $1. Earlier findings retained; evidence reassessed.",
  ],
  [/^Источник недоступен: HTTP (\d+)$/, "Source unavailable: HTTP $1"],
  [
    /^Не удалось проверить robots.txt \(HTTP (\d+)\); источник пропущен$/,
    "Could not check robots.txt (HTTP $1); source skipped",
  ],
  [
    /^Пользователь изменил оценку совпадения: (.*)$/,
    "User changed candidate review: $1",
  ],
  [
    /^Поиск запущен. Локальная модель: (.*)\.$/,
    "Research started. Local model: $1.",
  ],
  [
    /^Модель планирует этап (\d+): языки, варианты имени, новые направления\.$/,
    "Planning round $1: languages, name spellings and new directions.",
  ],
  [/^Добавлено поисковых запросов: (\d+)\.$/, "Search queries added: $1."],
  [/^Поиск \[(.*?)\]: (.*)$/, "Search [$1]: $2"],
  [
    /^Новых страниц в очереди: (\d+)\. Поисковые сниппеты не считаются доказательствами\.$/,
    "New pages queued: $1. Search snippets are not evidence.",
  ],
  [/^Чтение: (.*)$/, "Reading: $1"],
  [/^Локальная модель проверяет: (.*)$/, "Local model inspecting: $1"],
  [
    /^Возможных совпадений: (\d+)\. Отброшено цитат, которых нет в тексте: (\d+)\.$/,
    "Candidate cards: $1. Quotes missing from source text discarded: $2.",
  ],
  [
    /^Сервер вернул HTTP (\d+). Проверьте подключение и настройки\.$/,
    "Server returned HTTP $1. Check connection and settings.",
  ],
  [
    /^Локальная модель вернула HTTP (\d+). Проверьте модель, контекст и настройки JSON\.$/,
    "Local model returned HTTP $1. Check model, context and JSON settings.",
  ],
  [
    /^Поисковый источник недоступен \((.*?)\)\..*$/,
    "Search source unavailable ($1). Try again later or use local SearXNG.",
  ],
];
export function t(key: string, russian?: string): string {
  if (russian !== undefined) return prefs.language === "ru" ? russian : key;
  if (prefs.language === "ru") return reverse[key] || key;
  if ((messages as Record<string, string>)[key])
    return (messages as Record<string, string>)[key];
  for (const [pattern, replacement] of patterns)
    if (pattern.test(key)) return key.replace(pattern, replacement);
  return key;
}
export const locale = () => (prefs.language === "ru" ? "ru-RU" : "en-US");
