export const languages = [
  ["ru", "Русский"],
  ["en", "English"],
  ["uk", "Українська"],
  ["de", "Deutsch"],
  ["fr", "Français"],
  ["es", "Español"],
  ["it", "Italiano"],
  ["pt", "Português"],
  ["tr", "Türkçe"],
  ["pl", "Polski"],
  ["zh", "中文"],
  ["ja", "日本語"],
];
export const statusName: Record<string, string> = {
  draft: "Готов к запуску",
  queued: "В очереди",
  running: "Идёт поиск",
  paused: "На паузе",
  completed: "Завершён",
};
export const split = (v: string) =>
  v
    .split(/[,\n]/)
    .map((s) => s.trim())
    .filter(Boolean);
export const duration = (seconds: number) =>
  seconds < 60
    ? `${Math.floor(seconds)} сек`
    : `${Math.floor(seconds / 60)} мин`;
export const date = (value: string) =>
  new Date(value).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "short",
  });
export const host = (url: string) => {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
};
