import { useState, type FormEvent } from "react";
import {
  ChevronDown,
  Cpu,
  Globe2,
  Loader2,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import type { Models, Settings } from "../types";
import { Field, Modal } from "./ui";
export default function SettingsPanel({
  initial,
  models,
  probeModels,
  onSave,
  close,
}: {
  initial: Settings;
  models: Models;
  probeModels: (settings: Settings) => Promise<Models>;
  onSave: (s: Settings) => Promise<void>;
  close: () => void;
}) {
  const [settings, setSettings] = useState(initial);
  const [discovery, setDiscovery] = useState(models);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [checking, setChecking] = useState(false);
  const set = <K extends keyof Settings>(key: K, value: Settings[K]) =>
    setSettings((s) => ({ ...s, [key]: value }));
  async function submit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await onSave(settings);
      close();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }
  async function check() {
    setChecking(true);
    setError("");
    try {
      setDiscovery(await probeModels(settings));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setChecking(false);
    }
  }
  return (
    <Modal
      title="Настройки"
      subtitle="Вычисления только на вашем компьютере"
      close={close}
    >
      <form onSubmit={submit} className="settings-form">
        <div className="settings-section-title">
          <Cpu size={19} />
          <h3>Локальная модель</h3>
          <span className={`connection ${discovery.connected ? "online" : ""}`}>
            {discovery.connected ? "Сервер доступен" : "Нет соединения"}
          </span>
        </div>
        <Field
          label="Адрес сервера LM Studio"
          hint="В LM Studio включите Local Server. Поддерживаются только адреса этого компьютера."
        >
          {(id) => (
            <input
              id={id}
              required
              value={settings.model_url}
              onChange={(e) => set("model_url", e.target.value)}
            />
          )}
        </Field>
        <div className="model-row">
          <Field label="Модель">
            {(id) => (
              <select
                id={id}
                value={settings.model}
                onChange={(e) => set("model", e.target.value)}
              >
                <option value="">Выберите модель</option>
                {[
                  ...new Set([
                    ...(settings.model ? [settings.model] : []),
                    ...discovery.models,
                  ]),
                ].map((m) => (
                  <option key={m}>{m}</option>
                ))}
              </select>
            )}
          </Field>
          <button
            type="button"
            className="button secondary"
            onClick={check}
            disabled={checking}
          >
            <RefreshCw size={15} className={checking ? "spin" : ""} /> Проверить
          </button>
        </div>
        {!discovery.connected && (
          <p className="small-muted">
            {discovery.error ||
              "Модели появятся после подключения локального сервера."}
          </p>
        )}
        <p className="small-muted">
          При первом запросе LM Studio может загрузить выбранную модель в
          память. Приложение не скачивает модели автоматически.
        </p>
        <Field
          label="Режим модели"
          hint="Для Qwen 3.5 / 3.8 без доступного переключателя thinking в LM Studio предусмотрен отдельный совместимый шаблон."
        >
          {(id) => (
            <select
              id={id}
              value={settings.inference_mode}
              onChange={(e) =>
                setSettings((s) => ({
                  ...s,
                  inference_mode: e.target.value as Settings["inference_mode"],
                  structured_output: false,
                }))
              }
            >
              <option value="chat">Стандартный — шаблон LM Studio</option>
              <option value="qwen_no_thinking">
                Qwen 3 — без длинного thinking
              </option>
            </select>
          )}
        </Field>
        <details>
          <summary>
            Параметры генерации <ChevronDown size={15} />
          </summary>
          <div className="grid two">
            {(
              [
                ["temperature", "Температура", 0, 2, 0.05],
                ["top_p", "Top P", 0.01, 1, 0.01],
                ["max_tokens", "Лимит ответа, токены", 256, 16384, 1],
                ["context_chars", "Текст страницы, символы", 2000, 64000, 1000],
                ["model_timeout", "Ожидание модели, сек", 15, 1800, 1],
              ] as const
            ).map(([key, label, min, max, step]) => (
              <Field key={key} label={label}>
                {(id) => (
                  <input
                    id={id}
                    type="number"
                    min={min}
                    max={max}
                    step={step}
                    value={settings[key]}
                    onChange={(e) => set(key, +e.target.value)}
                  />
                )}
              </Field>
            ))}
          </div>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={settings.structured_output}
              disabled={settings.inference_mode === "qwen_no_thinking"}
              onChange={(e) => set("structured_output", e.target.checked)}
            />{" "}
            Запрашивать JSON Schema у модели
          </label>
          <p className="small-muted">
            Параметры загрузки модели, GPU и размер её контекста настраиваются в
            LM Studio. Слишком длинные ответы reasoning могут исчерпать лимит.
          </p>
        </details>
        <div className="form-divider" />
        <div className="settings-section-title">
          <Globe2 size={19} />
          <h3>Бесплатный веб-поиск</h3>
        </div>
        <Field label="Источник поиска">
          {(id) => (
            <select
              id={id}
              value={settings.search_provider}
              onChange={(e) =>
                set(
                  "search_provider",
                  e.target.value as Settings["search_provider"],
                )
              }
            >
              <option value="direct">Прямой поиск — без ключей и Docker</option>
              <option value="searxng">Мой локальный SearXNG</option>
            </select>
          )}
        </Field>
        {settings.search_provider === "searxng" ? (
          <Field
            label="Адрес SearXNG"
            hint="Требуется включённый JSON-формат выдачи."
          >
            {(id) => (
              <input
                id={id}
                value={settings.searxng_url}
                onChange={(e) => set("searxng_url", e.target.value)}
              />
            )}
          </Field>
        ) : (
          <div className="field">
            <label>Поисковые системы</label>
            <div className="chips">
              {["bing", "duckduckgo", "brave", "mojeek", "yahoo"].map(
                (backend) => (
                  <button
                    className={`chip ${settings.search_backends.includes(backend) ? "selected" : ""}`}
                    type="button"
                    key={backend}
                    aria-pressed={settings.search_backends.includes(backend)}
                    onClick={() =>
                      set(
                        "search_backends",
                        settings.search_backends.includes(backend)
                          ? settings.search_backends.length > 1
                            ? settings.search_backends.filter(
                                (b) => b !== backend,
                              )
                            : settings.search_backends
                          : [...settings.search_backends, backend],
                      )
                    }
                  >
                    {backend}
                  </button>
                ),
              )}
            </div>
          </div>
        )}
        <p className="small-muted">
          Поисковые системы могут ограничить запросы. Locus сообщает о
          недоступности и не обходит CAPTCHA. Платных подключений нет.
        </p>
        <div className="grid two">
          {(
            [
              ["results_per_query", "Результатов на запрос", 1, 30, 1],
              ["request_timeout", "Ожидание сайта, сек", 5, 90, 1],
              [
                "domain_delay",
                "Пауза между запросами к сайту, сек",
                1,
                30,
                0.5,
              ],
            ] as const
          ).map(([key, label, min, max, step]) => (
            <Field key={key} label={label}>
              {(id) => (
                <input
                  id={id}
                  type="number"
                  required
                  min={min}
                  max={max}
                  step={step}
                  value={settings[key]}
                  onChange={(e) => set(key, +e.target.value)}
                />
              )}
            </Field>
          ))}
        </div>
        <div className="notice">
          <ShieldCheck size={18} />
          <span>
            Нет облачных моделей, API-ключей, аналитики и внешних шрифтов.
            Содержимое страниц обрабатывается локально.
          </span>
        </div>
        {error && (
          <div className="inline-error" role="alert">
            {error}
          </div>
        )}
        <div className="modal-actions">
          <button type="button" className="button secondary" onClick={close}>
            Отмена
          </button>
          <button className="button primary" disabled={saving}>
            {saving && <Loader2 size={16} className="spin" />}Сохранить
            настройки
          </button>
        </div>
      </form>
    </Modal>
  );
}
