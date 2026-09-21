import { t } from "./i18n";
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch("/api" + path, {
    method,
    headers: { "Content-Type": "application/json", "X-Locus-Request": "1" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const data = await response
      .json()
      .catch(() => ({ detail: "Сервер недоступен" }));
    const message = Array.isArray(data.detail)
      ? data.detail
          .map((e: { msg: string }) => t(e.msg.replace("Value error, ", "")))
          .join(". ")
      : data.detail;
    throw new Error(t(message || `HTTP ${response.status}`));
  }
  return response.json();
}
