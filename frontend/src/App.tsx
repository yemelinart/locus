import { t, usePreferences, setPreferences } from "./i18n";
import { Trash2, ChartNoAxesCombined, Download } from "lucide-react";
import ReportDialog from "./components/ReportDialog";
import { useEffect, useState } from "react";
import {
  ArrowUpRight,
  Cpu,
  FileText,
  Layers3,
  Loader2,
  Plus,
  Settings2,
  ShieldCheck,
  Target,
  X,
  AlertCircle,
} from "lucide-react";
import type { Budget, Detail, Job, Models, Settings } from "./types";
import { statusName, date } from "./constants";
import { api } from "./api";
import { Badge, Modal, BudgetFields } from "./components/ui";
import NewResearch from "./components/NewResearch";
import SettingsPanel from "./components/SettingsPanel";
import ResearchView from "./components/ResearchView";
export default function App() {
  const prefs = usePreferences();
  const [selectedTab, setSelectedTab] = useState("candidates");
  const [deleteTarget, setDeleteTarget] = useState<Job | null>(null);
  const [exportTarget, setExportTarget] = useState<string | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [job, setJob] = useState<Detail | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [models, setModels] = useState<Models>({
    connected: false,
    models: [],
    error: "",
  });
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [budgetOpen, setBudgetOpen] = useState(false);
  const [budget, setBudget] = useState<Budget>({
    minutes: 30,
    queries: 40,
    pages: 80,
    rounds: 5,
  });
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const refreshModels = async () => {
    setModels(await api<Models>("/models"));
  };
  const refresh = async () => {
    setJobs(await api<Job[]>("/jobs"));
    if (selected) setJob(await api<Detail>(`/jobs/${selected}`));
  };
  useEffect(() => {
    Promise.all([api<Settings>("/settings"), api<Job[]>("/jobs")])
      .then(([s, j]) => {
        setSettings(s);
        setJobs(j);
        setReady(true);
      })
      .catch((e) =>
        setError(t("Не удалось подключиться к приложению. ") + e.message),
      );
    void refreshModels().catch(() => {});
  }, []);
  useEffect(() => {
    if (!selected) {
      setJob(null);
      return;
    }
    let alive = true;
    const load = async () => {
      try {
        const [detail, list] = await Promise.all([
          api<Detail>(`/jobs/${selected}`),
          api<Job[]>("/jobs"),
        ]);
        if (alive) {
          setJob(detail);
          setJobs(list);
        }
      } catch (e) {
        if (alive) setError((e as Error).message);
      }
    };
    void load();
    const timer = window.setInterval(load, 2500);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [selected]);
  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError("");
    try {
      await fn();
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  };
  const saveSettings = async (s: Settings) => {
    setSettings(await api<Settings>("/settings", "PUT", s));
    void refreshModels().catch(() => {});
  };
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setSelected(null);
          }}
          aria-label={t("Locus — новый поиск")}
        >
          <span className="brand-mark">
            <Target size={24} strokeWidth={1.6} />
          </span>
          <span>
            locus<span className="brand-dot">.</span>
          </span>
          <small>LOCAL</small>
        </a>
        <button
          className="new-button"
          onClick={() => {
            setSelected(null);
            setError("");
          }}
        >
          <Plus size={18} />
          {t("Новый поиск")}
          <span>↗</span>
        </button>
        <div className="nav-caption">{t("РАБОЧЕЕ ПРОСТРАНСТВО")}</div>
        <button
          className={`nav-item ${!selected ? "active" : ""}`}
          onClick={() => setSelected(null)}
        >
          <Layers3 size={18} />
          {t("Исследования")}
          <span>{jobs.length}</span>
        </button>
        <div className="history-title">{t("Последние поиски")}</div>
        <div className="job-list">
          {jobs.length ? (
            jobs.map((j) => (
              <div className="history-row" key={j.id}>
                <button
                  className={`job-link ${j.id === selected ? "selected" : ""}`}
                  onClick={() => {
                    setSelectedTab("candidates");
                    setSelected(j.id);
                    setError("");
                  }}
                >
                  <span className={`job-dot ${j.status}`} />
                  <div>
                    <strong>{j.name}</strong>
                    <small>
                      {statusName[j.status]} · {date(j.created_at)}
                    </small>
                  </div>
                  {j.status === "running" && (
                    <Loader2 size={13} className="spin" />
                  )}
                </button>
                <div className="history-actions">
                  <button
                    className="icon-button"
                    title={t("Analysis", "Анализ")}
                    aria-label={`${t("Analysis", "Анализ")}: ${j.name}`}
                    onClick={() => {
                      setSelected(j.id);
                      setSelectedTab("analysis");
                    }}
                  >
                    <ChartNoAxesCombined size={14} />
                  </button>
                  <button
                    className="icon-button"
                    title={t("Export", "Скачать")}
                    aria-label={`${t("Export", "Скачать")}: ${j.name}`}
                    onClick={() => setExportTarget(j.id)}
                  >
                    <Download size={14} />
                  </button>
                  <button
                    className="icon-button"
                    disabled={["running", "queued"].includes(j.status)}
                    title={t("Delete", "Удалить")}
                    aria-label={`${t("Delete", "Удалить")}: ${j.name}`}
                    onClick={() => {
                      setDeleteTarget(j);
                      setDeleteOpen(true);
                    }}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))
          ) : (
            <div className="no-history">
              <FileText size={20} />
              <p>
                {t("Ваши исследования")}
                <br />
                {t("будут сохранены здесь")}
              </p>
            </div>
          )}
        </div>
        <div className="sidebar-bottom">
          <div className="local-card">
            <span
              className={`connection-dot ${models.connected ? "online" : ""}`}
            />
            <div>
              <strong>
                {models.connected
                  ? t("LM Studio подключён")
                  : t("Подключите локальный ИИ")}
              </strong>
              <span>
                {settings?.model
                  ? t("Модель выбрана")
                  : t("Модель ещё не выбрана")}
              </span>
            </div>
            <Cpu size={18} />
          </div>
          <button
            className="nav-item settings-nav"
            onClick={() => setSettingsOpen(true)}
            disabled={!settings}
          >
            <Settings2 size={18} />
            {t("Настройки")}
            <ArrowUpRight size={15} />
          </button>
          <div className="sidebar-meta">
            <span>{t("v0.2 · ранняя версия")}</span>
            <span>{t("Открытый код")}</span>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <Layers3 size={15} />
            <span>{t("Исследования")}</span>
            <span>/</span>
            <strong>
              {selected
                ? job?.id === selected
                  ? job.name
                  : t("Загрузка…")
                : t("Новый поиск")}
            </strong>
          </div>
          <div className="topbar-right">
            <button
              className="language-toggle"
              aria-label={t(
                "Change interface language",
                "Изменить язык приложения",
              )}
              onClick={() =>
                setPreferences({
                  language: prefs.language === "en" ? "ru" : "en",
                })
              }
            >
              {prefs.language.toUpperCase()}
            </button>
            <span className="local-chip">
              <ShieldCheck size={14} />
              LOCAL FIRST
            </span>
            {job && selected === job.id && <Badge status={job.status} />}
          </div>
        </header>
        <main>
          {error && (
            <div className="error-banner" role="alert">
              <AlertCircle size={18} />
              <span>{t(error)}</span>
              <button
                onClick={() => setError("")}
                aria-label={t("Скрыть ошибку")}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {!ready ? (
            <div className="loading">
              <Loader2 className="spin" />
              {t("Загрузка локального пространства…")}
            </div>
          ) : selected ? (
            job && job.id === selected ? (
              <ResearchView
                key={`${job.id}-${selectedTab}`}
                initialTab={selectedTab}
                job={job}
                pending={busy}
                action={(action) =>
                  void run(async () => {
                    await api(`/jobs/${selected}/${action}`, "POST");
                    await refresh();
                  })
                }
                review={(id, status) =>
                  void run(async () => {
                    await api(
                      `/jobs/${selected}/candidates/${id}/review`,
                      "POST",
                      { status },
                    );
                    await refresh();
                  })
                }
                refine={(text) =>
                  run(async () => {
                    await api(`/jobs/${selected}/refine`, "POST", { text });
                    await refresh();
                  })
                }
                editBudget={() => {
                  setBudget(job.brief.budget);
                  setBudgetOpen(true);
                }}
                remove={() => {
                  setDeleteTarget(job);
                  setDeleteOpen(true);
                }}
              />
            ) : (
              <div className="loading">
                <Loader2 className="spin" />
                {t("Открываем исследование…")}
              </div>
            )
          ) : (
            <NewResearch
              busy={busy}
              configured={!!settings?.model}
              openSettings={() => setSettingsOpen(true)}
              onCreate={(brief) =>
                void run(async () => {
                  const created = await api<Job>("/jobs", "POST", brief);
                  setJobs(await api<Job[]>("/jobs"));
                  setSelected(created.id);
                })
              }
            />
          )}
        </main>
      </div>
      {exportTarget && (
        <ReportDialog id={exportTarget} close={() => setExportTarget(null)} />
      )}
      {settingsOpen && settings && (
        <SettingsPanel
          initial={settings}
          models={models}
          probeModels={(s) => api<Models>("/models/probe", "POST", s)}
          onSave={saveSettings}
          close={() => setSettingsOpen(false)}
        />
      )}
      {budgetOpen && (
        <Modal
          title={t("Бюджет исследования")}
          subtitle={t("Общий лимит с учётом уже выполненной работы")}
          close={() => setBudgetOpen(false)}
        >
          <form
            className="settings-form"
            onSubmit={(e) => {
              e.preventDefault();
              void run(async () => {
                await api(`/jobs/${selected}/budget`, "PUT", budget);
                setBudgetOpen(false);
                await refresh();
              });
            }}
          >
            <BudgetFields value={budget} onChange={setBudget} />
            <p className="small-muted">
              {t(
                "Если новых направлений нет, добавьте ориентиры и увеличьте число этапов. Увеличение времени само по себе не создаёт новые источники.",
              )}
            </p>
            <div className="modal-actions">
              <button className="button primary" disabled={busy}>
                {t("Сохранить бюджет")}
              </button>
            </div>
          </form>
        </Modal>
      )}
      {deleteOpen && (
        <Modal
          title={`${t("Delete research?", "Удалить исследование?")} ${deleteTarget?.name || ""}`}
          subtitle={t(
            "Его результаты, источники и история будут удалены с этого компьютера.",
          )}
          close={() => setDeleteOpen(false)}
        >
          <div className="modal-actions padded">
            <button
              className="button secondary"
              onClick={() => setDeleteOpen(false)}
            >
              {t("Отмена")}
            </button>
            <button
              className="button danger"
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  await api(`/jobs/${deleteTarget?.id}`, "DELETE");
                  if (selected === deleteTarget?.id) setSelected(null);
                  setDeleteTarget(null);
                  setDeleteOpen(false);
                  setJobs(await api<Job[]>("/jobs"));
                })
              }
            >
              {t("Удалить")}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
