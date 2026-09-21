import { t } from "../i18n";
import { useEffect, useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
import type { Budget } from "../types";
import { statusName } from "../constants";
export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: (id: string) => ReactNode;
}) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {children(id)}
      {hint && <span className="field-hint">{hint}</span>}
    </div>
  );
}
export function Badge({ status }: { status: string }) {
  return (
    <span className={`badge ${status}`}>
      <span className="status-dot" />
      {statusName[status] || status}
    </span>
  );
}
export function Modal({
  title,
  subtitle,
  close,
  children,
}: {
  title: string;
  subtitle?: string;
  close: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const titleId = useId();
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    const el = ref.current!;
    el.querySelector<HTMLElement>("button,input,select,textarea")?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      if (e.key !== "Tab") return;
      const focusables = [
        ...el.querySelectorAll<HTMLElement>(
          "button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href],summary",
        ),
      ].filter((item) => item.getClientRects().length > 0);
      const first = focusables[0],
        last = focusables.at(-1);
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last?.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
      previous?.focus();
    };
  }, []);
  return (
    <div
      className="overlay"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        ref={ref}
      >
        <div className="modal-head">
          <div>
            <h2 id={titleId}>{title}</h2>
            {subtitle && <p>{subtitle}</p>}
          </div>
          <button
            className="icon-button"
            onClick={close}
            aria-label={t("Закрыть")}
          >
            <X size={20} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function BudgetFields({
  value,
  onChange,
}: {
  value: Budget;
  onChange: (v: Budget) => void;
}) {
  return (
    <div className="grid four budget-fields">
      {(
        [
          ["minutes", t("Время, мин"), 43200],
          ["queries", t("Запросы"), 100000],
          ["pages", t("Страницы"), 100000],
          ["rounds", t("Этапы"), 10000],
        ] as const
      ).map(([key, label, max]) => (
        <Field key={key} label={label}>
          {(id) => (
            <input
              id={id}
              type="number"
              required
              min={1}
              max={max}
              value={value[key]}
              onChange={(e) =>
                onChange({ ...value, [key]: Number(e.target.value) })
              }
            />
          )}
        </Field>
      ))}
    </div>
  );
}
