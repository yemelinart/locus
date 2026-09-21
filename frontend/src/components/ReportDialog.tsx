import { FileText, Download, Braces } from "lucide-react";
import { Modal } from "./ui";
import { t, getPreferences } from "../i18n";
export default function ReportDialog({
  id,
  close,
}: {
  id: string;
  close: () => void;
}) {
  return (
    <Modal
      title={t("Export research", "Скачать исследование")}
      subtitle={t(
        "Overview, evidence, coverage and open questions.",
        "Обзор, свидетельства, охват и открытые вопросы.",
      )}
      close={close}
    >
      <div className="report-options">
        {(
          [
            [
              "pdf",
              "PDF",
              t(
                "A clean, paginated report with clickable sources.",
                "Чистая верстка, нумерация страниц и ссылки на источники.",
              ),
              FileText,
            ],
            [
              "md",
              "Markdown",
              t(
                "Structured text you can edit or keep in your notes.",
                "Структурированный текст для редактирования и заметок.",
              ),
              Download,
            ],
            [
              "json",
              "JSON",
              t(
                "Complete recorded data, including the activity analysis.",
                "Все записанные данные, включая анализ действий.",
              ),
              Braces,
            ],
          ] as const
        ).map(([format, label, hint, Icon]) => (
          <a
            key={format}
            className="report-option"
            href={`/api/jobs/${id}/export?format=${format}&lang=${getPreferences().language}`}
            download
          >
            <Icon size={23} />
            <span>
              <strong>{label}</strong>
              <small>{hint}</small>
            </span>
            <Download size={17} />
          </a>
        ))}
        <p className="small-muted">
          {t(
            "Exports are generated locally. Existing findings and verbatim quotes retain their language.",
            "Отчёты создаются локально. Прежние результаты и точные цитаты сохраняют исходный язык.",
          )}
        </p>
      </div>
    </Modal>
  );
}
