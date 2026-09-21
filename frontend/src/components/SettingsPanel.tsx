import { useEffect, useState, useRef, type FormEvent } from "react";
import {
  Check,
  ChevronDown,
  Cpu,
  Globe2,
  Loader2,
  RefreshCw,
  Palette,
  Info,
  SlidersHorizontal,
} from "lucide-react";
import type { Models, Settings, SearchEngine, SearchRun } from "../types";
import { Field, Modal } from "./ui";
import { api } from "../api";
import { t, usePreferences, setPreferences, type Preferences } from "../i18n";

const providerDefaults = {
  lmstudio: "http://127.0.0.1:1234/v1",
  ollama: "http://127.0.0.1:11434",
  openai_compatible: "http://127.0.0.1:8080/v1",
};
const modelKeys = [
  "model_provider",
  "model_url",
  "model",
  "inference_mode",
  "reasoning",
  "structured_output",
  "temperature",
  "top_p",
  "top_k",
  "min_p",
  "repeat_penalty",
  "max_tokens",
  "context_chars",
  "model_timeout",
] as const;
export default function SettingsPanel({
  initial,
  initialSection = "appearance",
  models,
  probeModels,
  onSave,
  close,
}: {
  initial: Settings;
  initialSection?: string;
  models: Models;
  probeModels: (settings: Settings) => Promise<Models>;
  onSave: (s: Settings) => Promise<void>;
  close: () => void;
}) {
  const prefs = usePreferences();
  const [tab, setTab] = useState(initialSection);
  const [settings, setSettings] = useState(initial),
    [discovery, setDiscovery] = useState(models);
  const [saving, setSaving] = useState(false),
    [error, setError] = useState(""),
    [checking, setChecking] = useState(false);
  const [catalog, setCatalog] = useState<SearchEngine[]>([]),
    [checks, setChecks] = useState<SearchRun[]>([]),
    [probing, setProbing] = useState(false);
  const probeRevision = useRef(0);
  const providerDrafts = useRef<
    Partial<Record<Settings["model_provider"], Settings>>
  >({});
  const provider = settings.model_provider || "lmstudio";
  const nativeControls =
    provider === "ollama" || settings.inference_mode === "lmstudio";
  function invalidateDiscovery() {
    probeRevision.current++;
    setChecking(false);
    setDiscovery({ connected: false, models: [], error: "" });
    setError("");
  }
  function chooseProvider(next: Settings["model_provider"]) {
    providerDrafts.current[provider] = settings;
    const saved = providerDrafts.current[next];
    const patch = saved
      ? Object.fromEntries(modelKeys.map((k) => [k, saved[k]]))
      : {
          model_provider: next,
          model_url: providerDefaults[next],
          model: "",
          inference_mode: "chat",
          reasoning: "default",
          structured_output: false,
        };
    setSettings((s) => ({
      ...s,
      ...patch,
      inference_mode: "chat",
      reasoning: "default",
      structured_output: false,
    }));
    invalidateDiscovery();
  }
  const set = <K extends keyof Settings>(key: K, value: Settings[K]) =>
    setSettings((s) => ({ ...s, [key]: value }));
  useEffect(() => {
    api<SearchEngine[]>("/search/catalog")
      .then(setCatalog)
      .catch((e) => setError(e.message));
  }, []);
  const capability = discovery.capabilities?.find(
    (m) =>
      m.key === settings.model ||
      m.instances.some((i) => i.id === settings.model),
  );
  async function check(value = settings) {
    const revision = ++probeRevision.current;
    setChecking(true);
    setError("");
    try {
      const result = await probeModels(value);
      if (revision === probeRevision.current) setDiscovery(result);
    } catch (e) {
      if (revision === probeRevision.current) setError((e as Error).message);
    } finally {
      if (revision === probeRevision.current) setChecking(false);
    }
  }
  async function submit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await onSave({ ...settings, response_language: prefs.language });
      close();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }
  function recommend() {
    if (tab === "search") {
      setSettings((s) => ({
        ...s,
        search_backends: ["duckduckgo", "brave"].filter((e) =>
          catalog.some((c) => c.id === e && c.available),
        ),
        results_per_query: 8,
        request_timeout: 20,
        domain_delay: 1.5,
        safesearch: "moderate",
        search_region: "auto",
      }));
      return;
    }
    setSettings((s) => ({
      ...s,
      temperature: 0.1,
      top_p: 0.9,
      top_k: 40,
      min_p: 0.05,
      repeat_penalty: 1,
      max_tokens: 2400,
      context_chars: 16000,
      model_timeout: 300,
      structured_output: false,
      reasoning: capability?.reasoning_options.includes("off")
        ? "off"
        : "default",
      inference_mode:
        provider !== "lmstudio"
          ? "chat"
          : capability?.reasoning_options.length
            ? "lmstudio"
            : /qwen.?3/i.test(s.model)
              ? "qwen_no_thinking"
              : "chat",
    }));
  }
  const number = (
    key: keyof Settings,
    label: string,
    min: number,
    max: number,
    step: number,
    hint: string,
  ) => (
    <Field key={key} label={label} hint={hint}>
      {(id) => (
        <input
          id={id}
          type="number"
          required
          min={min}
          max={max}
          step={step}
          value={settings[key] as number}
          onChange={(e) => set(key, +e.target.value)}
        />
      )}
    </Field>
  );
  return (
    <Modal
      title={t("Settings", "Настройки")}
      subtitle={t(
        "Your workspace, your local intelligence.",
        "Ваше пространство и ваш локальный ИИ.",
      )}
      close={close}
    >
      <div
        className="settings-tabs"
        role="tablist"
        aria-label={t("Settings sections", "Разделы настроек")}
      >
        {(
          [
            ["appearance", t("Appearance", "Оформление"), Palette],
            ["model", t("Local AI", "Локальный ИИ"), Cpu],
            ["search", t("Web search", "Веб-поиск"), Globe2],
            ["about", t("About", "О программе"), Info],
          ] as const
        ).map(([key, label, Icon]) => (
          <button
            key={key}
            role="tab"
            aria-selected={tab === key}
            className={tab === key ? "active" : ""}
            onClick={() => setTab(key)}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>
      <form onSubmit={submit} className="settings-form">
        {tab === "appearance" && (
          <section className="appearance-panel">
            <h3>
              {t(
                "Make it feel like your space",
                "Настройте пространство под себя",
              )}
            </h3>
            <Field
              label={t("Interface language", "Язык приложения")}
              hint={t(
                "New research uses this language for explanations. Existing findings and original quotes stay unchanged.",
                "Новые исследования используют этот язык для пояснений. Прежние результаты и цитаты сохраняют исходный язык.",
              )}
            >
              {(id) => (
                <select
                  id={id}
                  value={prefs.language}
                  onChange={(e) =>
                    setPreferences({
                      language: e.target.value as Preferences["language"],
                    })
                  }
                >
                  <option value="en">English</option>
                  <option value="ru">Русский</option>
                </select>
              )}
            </Field>
            <div className="field">
              <label>{t("Colour palette", "Цветовая палитра")}</label>
              <div className="palette-grid">
                {(
                  [
                    ["forest", t("Forest", "Лес"), "#345943", "#aebf92"],
                    ["ocean", t("Ocean", "Океан"), "#285981", "#9bbdd5"],
                    ["sand", t("Sand", "Песок"), "#755537", "#d1b88e"],
                    ["graphite", t("Graphite", "Графит"), "#424d64", "#b3bacc"],
                  ] as const
                ).map(([key, label, a, b]) => (
                  <button
                    key={key}
                    type="button"
                    className={`palette-card ${prefs.palette === key ? "selected" : ""}`}
                    aria-pressed={prefs.palette === key}
                    onClick={() => setPreferences({ palette: key })}
                  >
                    <span
                      className="swatch"
                      style={{
                        background: `linear-gradient(120deg,${a} 50%,${b} 50%)`,
                      }}
                    />
                    {label}
                    {prefs.palette === key && <Check size={15} />}
                  </button>
                ))}
              </div>
            </div>
            <div className="field">
              <label>{t("Brightness", "Яркость")}</label>
              <div className="segmented">
                {(
                  [
                    ["light", t("Light", "Светлая")],
                    ["soft", t("Soft", "Приглушённая")],
                    ["dark", t("Dark", "Тёмная")],
                  ] as const
                ).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    aria-pressed={prefs.tone === key}
                    className={prefs.tone === key ? "selected" : ""}
                    onClick={() => setPreferences({ tone: key })}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <div className="theme-preview">
              <span className="eyebrow">LOCUS / YOUR WORKSPACE</span>
              <h2>
                {t("Clarity, in every detail.", "Ясность в каждой детали.")}
              </h2>
              <p>
                {t(
                  "Colours and language are saved immediately on this browser.",
                  "Цвета и язык сразу сохраняются в этом браузере.",
                )}
              </p>
              <span className="badge completed">
                {t("Evidence first", "Сначала свидетельства")}
              </span>
            </div>
          </section>
        )}
        {tab === "model" && (
          <>
            <div className="settings-section-title">
              <Cpu size={19} />
              <h3>{t("Local model", "Локальная модель")}</h3>
              <span
                className={`connection ${discovery.connected ? "online" : ""}`}
              >
                {discovery.connected
                  ? t("Server connected", "Сервер доступен")
                  : t("Not connected", "Нет соединения")}
              </span>
            </div>
            <Field
              label={t("AI provider", "ИИ-провайдер")}
              hint={t(
                "Choose the app serving your model. All inference stays on this computer.",
                "Выберите приложение, которое запускает модель. ИИ работает на этом компьютере.",
              )}
            >
              {(id) => (
                <select
                  id={id}
                  value={provider}
                  onChange={(e) =>
                    chooseProvider(e.target.value as Settings["model_provider"])
                  }
                >
                  <option value="lmstudio">LM Studio</option>
                  <option value="ollama">Ollama</option>
                  <option value="openai_compatible">
                    {t(
                      "Other local server (OpenAI-compatible)",
                      "Другой локальный сервер (OpenAI-compatible)",
                    )}
                  </option>
                </select>
              )}
            </Field>
            <div className="provider-guide">
              {provider === "lmstudio"
                ? t(
                    "In LM Studio, enable the local server in Developer. Then refresh models and choose one below.",
                    "В LM Studio включите локальный сервер в Developer. Затем обновите список моделей и выберите нужную.",
                  )
                : provider === "ollama"
                  ? t(
                      "Start Ollama and download a chat model there. Refresh models below. Locus does not install, download or load models during this check; remote/cloud models are not supported.",
                      "Запустите Ollama и скачайте в ней чат-модель. Обновите список ниже. Проверка не устанавливает, не скачивает и не загружает модели в память; облачные модели не поддерживаются.",
                    )
                  : t(
                      "For a local server such as llama.cpp: enter its OpenAI-compatible base address ending in /v1. It must provide /models and /chat/completions. Keep model loading and context settings in that server.",
                      "Для локального сервера, например llama.cpp: укажите совместимый адрес, заканчивающийся на /v1. Нужна поддержка /models и /chat/completions. Загрузка модели и её контекст настраиваются в сервере.",
                    )}
            </div>
            <Field
              label={
                provider === "lmstudio"
                  ? t("LM Studio server address", "Адрес сервера LM Studio")
                  : t("Server address", "Адрес сервера")
              }
              hint={t(
                "Loopback only: localhost or 127.0.0.1, with the server port.",
                "Только localhost или 127.0.0.1 с портом сервера.",
              )}
            >
              {(id) => (
                <input
                  id={id}
                  required
                  value={settings.model_url}
                  onChange={(e) => {
                    setSettings((s) => ({
                      ...s,
                      model_url: e.target.value,
                      model: "",
                      reasoning: "default",
                      inference_mode: "chat",
                      structured_output: false,
                    }));
                    invalidateDiscovery();
                  }}
                />
              )}
            </Field>
            <div className="model-row">
              <Field label={t("Model", "Модель")}>
                {(id) => (
                  <select
                    id={id}
                    value={settings.model}
                    onChange={(e) => {
                      const next: Settings = {
                        ...settings,
                        model: e.target.value,
                        reasoning: "default",
                        inference_mode: "chat",
                        structured_output: false,
                      };
                      setSettings(next);
                      if (provider === "ollama") void check(next);
                    }}
                  >
                    <option value="">
                      {t("Choose a model", "Выберите модель")}
                    </option>
                    {[
                      ...new Set([
                        ...(settings.model ? [settings.model] : []),
                        ...discovery.models,
                        ...(discovery.capabilities || []).map((m) => m.key),
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
                onClick={() => void check()}
                disabled={checking}
              >
                <RefreshCw size={15} className={checking ? "spin" : ""} />
                {t("Refresh models", "Проверить модели")}
              </button>
            </div>
            {discovery.error && (
              <p className="small-muted">{t(discovery.error)}</p>
            )}
            {discovery.capability_error && (
              <p className="small-muted">{t(discovery.capability_error)}</p>
            )}
            {!!discovery.excluded_models && (
              <p className="small-muted">
                {t("Remote models hidden: ", "Облачных моделей скрыто: ")}
                {discovery.excluded_models}
              </p>
            )}
            {discovery.connected && !discovery.models.length && (
              <p className="small-muted">
                {t(
                  "No local chat models found. Download one in your provider app, then refresh.",
                  "Локальные чат-модели не найдены. Скачайте модель в приложении-провайдере и обновите список.",
                )}
              </p>
            )}
            {capability && (
              <div className="capability-card">
                <strong>{capability.name}</strong>
                <span>
                  {capability.instances.length
                    ? t("Loaded", "Загружена")
                    : t("Available on disk", "Есть на диске")}{" "}
                  · {capability.architecture} ·{" "}
                  {t("Max context", "Макс. контекст")}:{" "}
                  {capability.max_context?.toLocaleString()}
                </span>
                {capability.instances.map((i) => (
                  <small key={i.id}>
                    {i.id} · {t("Loaded context", "Загруженный контекст")}:{" "}
                    {i.config?.context_length?.toLocaleString()}
                  </small>
                ))}
              </div>
            )}
            {provider === "lmstudio" && (
              <Field
                label={t("Inference mode", "Режим модели")}
                hint={t(
                  "Native mode reads capabilities from LM Studio. The compatible Qwen mode closes its thinking block without editing the model.",
                  "Нативный режим читает возможности LM Studio. Совместимый режим Qwen закрывает блок thinking без изменения файлов модели.",
                )}
              >
                {(id) => (
                  <select
                    id={id}
                    value={settings.inference_mode}
                    onChange={(e) =>
                      setSettings((s) => ({
                        ...s,
                        inference_mode: e.target
                          .value as Settings["inference_mode"],
                        structured_output: false,
                        reasoning: "default",
                      }))
                    }
                  >
                    <option value="chat">
                      {t("Standard local chat", "Стандартный локальный чат")}
                    </option>
                    <option value="lmstudio" disabled={!capability}>
                      {t(
                        "LM Studio native controls",
                        "Нативные настройки LM Studio",
                      )}
                    </option>
                    <option
                      value="qwen_no_thinking"
                      disabled={!/qwen.?3/i.test(settings.model)}
                    >
                      {t(
                        "Qwen 3 — thinking off (compatible)",
                        "Qwen 3 — без thinking (совместимый)",
                      )}
                    </option>
                  </select>
                )}
              </Field>
            )}
            {nativeControls && (
              <Field
                label={t("Thinking level", "Уровень thinking")}
                hint={t(
                  "Available controls come from server metadata or documented model families. Default preserves model behaviour. More thinking can take longer and consume the output budget.",
                  "Доступные режимы определяются по данным сервера или документации семейства модели. «По умолчанию» сохраняет поведение модели. Долгий thinking расходует время и лимит ответа.",
                )}
              >
                {(id) => (
                  <select
                    id={id}
                    value={settings.reasoning}
                    onChange={(e) => set("reasoning", e.target.value)}
                  >
                    <option value="default">
                      {t("Model default", "По умолчанию модели")}
                      {capability?.reasoning_default
                        ? ` (${capability.reasoning_default})`
                        : ""}
                    </option>
                    {capability?.reasoning_options.map((v) => (
                      <option key={v} value={v}>
                        {v}
                      </option>
                    ))}
                  </select>
                )}
              </Field>
            )}
            {!capability?.reasoning_options.length && (
              <p className="small-muted">
                {t(
                  "This server has not exposed adjustable thinking levels for the selected model. This does not mean the model cannot reason.",
                  "Сервер не объявил переключаемые уровни thinking для выбранной модели. Это не означает, что модель не умеет рассуждать.",
                )}
              </p>
            )}
            <p className="small-muted">
              {t(
                "Usually you do not need to tune these values. Apply the recommended preset, run a short search, and change one parameter only when there is a specific problem. This preset favours restrained extraction; follow model-specific guidance if needed.",
                "Обычно эти значения менять не нужно. Примените рекомендуемый шаблон, запустите короткий поиск и меняйте по одному параметру только при конкретной проблеме. Шаблон рассчитан на сдержанное извлечение; при необходимости учитывайте рекомендации автора модели.",
              )}
            </p>
            <button
              type="button"
              className="button secondary"
              onClick={recommend}
            >
              <Check size={16} />
              {t(
                "Apply recommended settings",
                "Применить рекомендуемые настройки",
              )}
            </button>
            <details>
              <summary>
                <SlidersHorizontal size={16} />
                {t("Manual settings & guide", "Ручные настройки и пояснения")}
                <ChevronDown size={15} />
              </summary>
              <div className="grid two">
                {number(
                  "temperature",
                  t("Temperature", "Температура"),
                  0,
                  settings.inference_mode === "lmstudio" ? 1 : 2,
                  0.05,
                  t(
                    "Controls variation in wording. 0–0.2 is a starting point for extraction; higher values are more varied, not more factual. Follow your model’s guidance.",
                    "Разнообразие ответов. 0–0,2 — отправная точка для извлечения. Выше — разнообразнее, но не достовернее. Учитывайте рекомендации модели.",
                  ),
                )}
                {number(
                  "top_p",
                  "Top P",
                  0.01,
                  1,
                  0.01,
                  t(
                    "Restricts choices to tokens covering this share of probability. 0.9 = 90%. Usually leave it; avoid tuning it together with temperature.",
                    "Ограничивает выбор словами/фрагментами с этой суммарной вероятностью. 0,9 = 90%. Обычно оставьте как есть и не меняйте одновременно с температурой.",
                  ),
                )}
                {number(
                  "max_tokens",
                  t("Output token budget", "Лимит ответа, токены"),
                  256,
                  16384,
                  1,
                  t(
                    "Maximum generated answer, measured in text fragments (tokens), not words. Start at 2400. Raise it for truncated JSON; thinking may consume this budget too.",
                    "Максимум ответа в токенах — фрагментах текста, не словах. Начните с 2400. Увеличьте при обрезанном JSON; thinking тоже может расходовать этот лимит.",
                  ),
                )}
                {number(
                  "context_chars",
                  t("Page excerpt, characters", "Текст страницы, символы"),
                  2000,
                  64000,
                  1000,
                  t(
                    "Characters read from each page for the model. Start at 16000. More text may reveal more evidence but needs more memory/context. Reduce it if the prompt is too long.",
                    "Символы страницы, передаваемые модели. Начните с 16000. Больше текста — больше материала, но выше требования к памяти и контексту. Уменьшите, если запрос не помещается.",
                  ),
                )}
                {number(
                  "model_timeout",
                  t("Model timeout, seconds", "Ожидание модели, сек"),
                  15,
                  1800,
                  1,
                  t(
                    "Seconds allowed for one model response. Start at 300; increase for slower models. This does not make the model faster or extend the research time budget.",
                    "Секунды ожидания одного ответа. Начните с 300, увеличьте для медленной модели. Это не ускоряет модель и не продлевает общий бюджет исследования.",
                  ),
                )}
                {nativeControls && (
                  <>
                    {number(
                      "top_k",
                      "Top K",
                      1,
                      1000,
                      1,
                      t(
                        "How many likely next-token choices remain. 40 is a starting point; lower is narrower. Usually leave unchanged. Sent only through native provider controls.",
                        "Сколько вероятных вариантов следующего фрагмента оставить. Начальное значение — 40; меньше — уже выбор. Обычно менять не нужно. Передаётся через нативные настройки провайдера.",
                      ),
                    )}
                    {number(
                      "min_p",
                      "Min P",
                      0,
                      1,
                      0.01,
                      t(
                        "Drops unlikely choices relative to the best one. 0 disables this filter; 0.05 is the preset. Usually leave unchanged.",
                        "Отбрасывает маловероятные варианты относительно лучшего. 0 отключает фильтр; в шаблоне 0,05. Обычно оставьте как есть.",
                      ),
                    )}
                    {number(
                      "repeat_penalty",
                      t("Repetition penalty", "Штраф повторений"),
                      1,
                      2,
                      0.05,
                      t(
                        "1 adds no penalty. Values above 1 discourage repetition, but can damage exact quotes and names. For research, usually keep 1.",
                        "1 — без штрафа. Выше 1 уменьшает повторы, но может искажать точные цитаты и имена. Для исследования обычно оставьте 1.",
                      ),
                    )}
                  </>
                )}
              </div>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={settings.structured_output}
                  disabled={settings.inference_mode !== "chat"}
                  onChange={(e) => set("structured_output", e.target.checked)}
                />
                {t(
                  "Request JSON Schema (when supported)",
                  "Запрашивать JSON Schema (при поддержке)",
                )}
              </label>
              <p className="small-muted">
                {t(
                  "JSON Schema helps keep answers structured. Enable it only when supported; if the server rejects the format, turn it off. Locus validates every answer either way.",
                  "JSON Schema помогает соблюдать структуру ответа. Включайте при поддержке сервером; при ошибке формата отключите. Locus в любом случае проверяет структуру ответа.",
                )}
              </p>
              <p className="small-muted">
                {t(
                  "GPU, memory and the model’s context window are configured in your provider app. Locus sends generation settings per request; it does not edit model files or global provider settings.",
                  "GPU, память и окно контекста настраиваются в приложении-провайдере. Locus передаёт параметры для отдельного запроса, не редактируя файлы модели и глобальные настройки.",
                )}
              </p>
            </details>
          </>
        )}
        {tab === "search" && (
          <>
            <h3>{t("Free web search", "Бесплатный веб-поиск")}</h3>
            <Field label={t("Search provider", "Источник поиска")}>
              {(id) => (
                <select
                  id={id}
                  value={settings.search_provider}
                  onChange={(e) => {
                    setSettings((s) => ({
                      ...s,
                      search_provider: e.target
                        .value as Settings["search_provider"],
                      search_backends: s.search_backends.length
                        ? s.search_backends
                        : ["duckduckgo"],
                    }));
                    setChecks([]);
                  }}
                >
                  <option value="direct">
                    {t(
                      "Direct — no keys or Docker",
                      "Прямой — без ключей и Docker",
                    )}
                  </option>
                  <option value="searxng">
                    {t("My local SearXNG", "Мой локальный SearXNG")}
                  </option>
                </select>
              )}
            </Field>
            {settings.search_provider === "searxng" ? (
              <Field
                label={t("SearXNG address", "Адрес SearXNG")}
                hint={t(
                  "Enable JSON output in your own local instance.",
                  "Включите JSON-выдачу в своём локальном экземпляре.",
                )}
              >
                {(id) => (
                  <input
                    id={id}
                    value={settings.searxng_url}
                    onChange={(e) => {
                      set("searxng_url", e.target.value);
                      setChecks([]);
                    }}
                  />
                )}
              </Field>
            ) : (
              <div className="engine-grid">
                {catalog.map((engine) => {
                  const enabled = settings.search_backends.includes(engine.id);
                  const result = checks.find((c) => c.engine === engine.id);
                  return (
                    <button
                      type="button"
                      key={engine.id}
                      className={`engine-card ${enabled && engine.available ? "selected" : ""}`}
                      aria-pressed={enabled && engine.available}
                      disabled={!engine.available}
                      onClick={() =>
                        set(
                          "search_backends",
                          enabled
                            ? settings.search_backends.filter(
                                (e) => e !== engine.id,
                              )
                            : [...settings.search_backends, engine.id],
                        )
                      }
                    >
                      <span className="engine-logo">{engine.name[0]}</span>
                      <span className="engine-copy">
                        <strong>{engine.name}</strong>
                        <small>
                          {!engine.available
                            ? t("Adapter unavailable", "Адаптер недоступен")
                            : result
                              ? {
                                  ok: t("Responded", "Ответ получен"),
                                  empty: t(
                                    "No test results",
                                    "Нет тестовых результатов",
                                  ),
                                  failed: t("Check failed", "Ошибка проверки"),
                                }[result.status] || result.status
                              : t("Not tested", "Не проверено")}
                        </small>
                      </span>
                      <span
                        className={`toggle ${enabled && engine.available ? "on" : ""}`}
                        aria-hidden="true"
                      >
                        <span />
                      </span>
                      <span className="sr-only">
                        {enabled
                          ? t("Enabled", "Включено")
                          : t("Disabled", "Выключено")}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
            {!settings.search_backends.length &&
              settings.search_provider === "direct" && (
                <p role="alert" className="inline-error">
                  {t(
                    "Select at least one search engine.",
                    "Выберите хотя бы одну поисковую систему.",
                  )}
                </p>
              )}
            <div className="inline-actions">
              <button
                type="button"
                className="button secondary"
                disabled={
                  probing ||
                  (!settings.search_backends.length &&
                    settings.search_provider === "direct")
                }
                onClick={async () => {
                  setProbing(true);
                  setError("");
                  try {
                    setChecks(
                      await api<SearchRun[]>("/search/probe", "POST", settings),
                    );
                  } catch (e) {
                    setError((e as Error).message);
                  } finally {
                    setProbing(false);
                  }
                }}
              >
                <RefreshCw size={15} className={probing ? "spin" : ""} />
                {t("Test enabled engines", "Проверить включённые")}
              </button>
              <button type="button" className="button text" onClick={recommend}>
                {t("Recommended settings", "Рекомендуемые настройки")}
              </button>
            </div>
            {settings.search_provider === "searxng" &&
              checks.map((c) => (
                <p key={c.engine}>
                  {c.engine}: {c.status}
                </p>
              ))}
            {checks.length > 0 && (
              <p className="small-muted">
                {t(
                  "Test completed in this session. Availability can change; enabled is not the same as connected.",
                  "Проверка выполнена в этой сессии. Доступность может измениться; включено не означает подключено.",
                )}
              </p>
            )}
            <p className="small-muted">
              {t(
                "Testing sends a neutral Python query, never your research name. During research, engines rotate with one fallback; every actual attempt is recorded. Wikipedia is a reference source, not a full web index.",
                "Проверка отправляет нейтральный запрос о Python, не имя из исследования. В поиске системы чередуются с одной резервной попыткой; все обращения записываются. Wikipedia — справочник, а не полный веб-индекс.",
              )}
            </p>
            <details>
              <summary>
                <SlidersHorizontal size={16} />
                {t(
                  "Manual search settings & guide",
                  "Ручные настройки поиска и пояснения",
                )}
                <ChevronDown size={15} />
              </summary>
              <div className="grid two">
                {number(
                  "results_per_query",
                  t("Results per query", "Результатов на запрос"),
                  1,
                  30,
                  1,
                  t(
                    "Start with 8. More results mean more pages to inspect.",
                    "Начните с 8. Больше результатов — больше страниц для чтения.",
                  ),
                )}
                {number(
                  "request_timeout",
                  t("Website timeout, seconds", "Ожидание сайта, сек"),
                  5,
                  90,
                  1,
                  t(
                    "A timeout is not evidence of no matches.",
                    "Тайм-аут не доказывает отсутствие совпадений.",
                  ),
                )}
                {number(
                  "domain_delay",
                  t(
                    "Domain delay, seconds",
                    "Пауза между запросами к сайту, сек",
                  ),
                  1,
                  30,
                  0.5,
                  t(
                    "Spacing between page requests to the same website.",
                    "Пауза между чтением страниц одного сайта.",
                  ),
                )}
                <Field
                  label="SafeSearch"
                  hint={t(
                    "Search engines may interpret these filters differently.",
                    "Поисковые системы могут по-разному применять фильтр.",
                  )}
                >
                  {(id) => (
                    <select
                      id={id}
                      value={settings.safesearch}
                      onChange={(e) =>
                        set(
                          "safesearch",
                          e.target.value as Settings["safesearch"],
                        )
                      }
                    >
                      {["on", "moderate", "off"].map((v) => (
                        <option key={v}>{v}</option>
                      ))}
                    </select>
                  )}
                </Field>
                <Field
                  label={t("Search region", "Регион поиска")}
                  hint={t(
                    "Automatic follows each query language; a fixed region biases results.",
                    "Автоматический режим следует языку запроса; фиксированный регион влияет на выдачу.",
                  )}
                >
                  {(id) => (
                    <select
                      id={id}
                      value={settings.search_region}
                      onChange={(e) => set("search_region", e.target.value)}
                    >
                      {[
                        "auto",
                        "wt-wt",
                        "us-en",
                        "ca-en",
                        "gb-en",
                        "ua-uk",
                        "ru-ru",
                        "de-de",
                        "fr-fr",
                        "tr-tr",
                      ].map((v) => (
                        <option key={v}>{v}</option>
                      ))}
                    </select>
                  )}
                </Field>
              </div>
            </details>
          </>
        )}
        {tab === "about" && (
          <section className="about-panel">
            <div className="about-mark">locus.</div>
            <span className="badge completed">
              v0.3 · {t("Local research", "Локальный поиск")}
            </span>
            <h2>VibeCoded by Sergey Yemelin</h2>
            <p>
              {t(
                "Built and rechecked with ChatGPT 6 Astra.",
                "Сделано и перепроверено с ChatGPT 6 Astra.",
              )}
            </p>
            <div className="form-divider" />
            <p>
              {t(
                "Open-source code under the MIT license. No subscriptions, paid search APIs or cloud inference are required.",
                "Открытый код под лицензией MIT. Подписки, платные поисковые API и облачный ИИ не требуются.",
              )}
            </p>
            <p className="small-muted">
              {t(
                "All model reasoning runs on your computer. Search engines receive your queries and websites receive page requests. LM Studio and model weights have their own licenses.",
                "ИИ работает на вашем компьютере. Поисковики получают запросы, сайты — обращения к страницам. У LM Studio и весов моделей отдельные лицензии.",
              )}
            </p>
            <h3>{t("A practical starting point", "С чего начать")}</h3>
            <ol className="mini-guide">
              <li>
                {t(
                  "Connect a local model and apply the recommended settings.",
                  "Подключите локальную модель и примените рекомендуемые настройки.",
                )}
              </li>
              <li>
                {t(
                  "Add a name, one useful context clue and relevant languages.",
                  "Добавьте имя, один полезный ориентир и нужные языки.",
                )}
              </li>
              <li>
                {t(
                  "Start with a small budget. Inspect sources and contradictions before increasing it.",
                  "Начните с небольшого бюджета. Изучите источники и противоречия перед расширением.",
                )}
              </li>
              <li>
                {t(
                  "Treat spelling variants as hypotheses, not proof that profiles belong to the same person.",
                  "Считайте варианты написания гипотезами, а не доказательством принадлежности профилей одному человеку.",
                )}
              </li>
            </ol>
          </section>
        )}
        {error && (
          <div className="inline-error" role="alert">
            {t(error)}
          </div>
        )}
        <div className="modal-actions">
          <button type="button" className="button secondary" onClick={close}>
            {t("Close", "Закрыть")}
          </button>
          {(tab === "model" || tab === "search") && (
            <button
              className="button primary"
              disabled={
                saving ||
                (!settings.search_backends.length &&
                  settings.search_provider === "direct")
              }
            >
              {saving && <Loader2 size={16} className="spin" />}
              {t("Save settings", "Сохранить настройки")}
            </button>
          )}
        </div>
      </form>
    </Modal>
  );
}
