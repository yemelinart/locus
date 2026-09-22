import {
  ArrowRight,
  BookOpen,
  Cpu,
  FileCheck2,
  FolderArchive,
  Languages,
  SlidersHorizontal,
} from "lucide-react";
import { t } from "../i18n";

export default function Welcome({
  start,
  settings,
}: {
  start: () => void;
  settings: () => void;
}) {
  const features = [
    [
      Cpu,
      t("Your computer does the thinking", "ИИ работает на вашем компьютере"),
      t(
        "Connect LM Studio, Ollama or a compatible local server. Choose your own model and generation settings.",
        "Подключите LM Studio, Ollama или совместимый локальный сервер. Выбирайте модель и параметры генерации.",
      ),
    ],
    [
      FileCheck2,
      t("Follow the evidence", "Проверяйте источники"),
      t(
        "Each claim needs a source quotation and a separate local AI review of its meaning and subject. Inspect the links, then confirm or reject the candidate yourself.",
        "Для каждого утверждения нужны цитата и отдельная проверка её смысла и принадлежности локальным ИИ. Изучите ссылки, затем подтвердите или отклоните кандидата сами.",
      ),
    ],
    [
      Languages,
      t("Search across languages", "Ищите на разных языках"),
      t(
        "Add name variants, former names and known context. Plan queries in any of 12 supported languages.",
        "Добавьте варианты написания, прежние имена и известный контекст. Планируйте запросы на 12 поддерживаемых языках.",
      ),
    ],
    [
      SlidersHorizontal,
      t("Set the scope", "Управляйте глубиной"),
      t(
        "Choose search engines, sites and limits for time, queries and pages. Pause, review and continue when you decide.",
        "Выбирайте поисковики, сайты и лимиты времени, запросов и страниц. Ставьте на паузу, проверяйте и продолжайте по своему решению.",
      ),
    ],
    [
      FolderArchive,
      t("Build on what you find", "Продолжайте с найденного"),
      t(
        "Keep a research project with its sources and history. Add clues, revise criteria and export PDF, Markdown, JSON or a project ZIP.",
        "Сохраняйте исследование с источниками и историей. Добавляйте ориентиры, уточняйте критерии и скачивайте PDF, Markdown, JSON или ZIP проекта.",
      ),
    ],
    [
      BookOpen,
      t("Make it your workspace", "Настройте под себя"),
      t(
        "English and Russian, four colour palettes and three brightness levels. MIT-licensed source code, no Locus subscription.",
        "Английский и русский, четыре палитры и три уровня яркости. Код под лицензией MIT, без подписки на Locus.",
      ),
    ],
  ] as const;
  const steps = [
    [
      t("Connect local AI", "Подключите локальный ИИ"),
      t(
        "Install LM Studio or Ollama, download a chat model and start its local server. In Settings → Local AI, choose the provider, address and model, then save. Recommended settings are a starting point.",
        "Установите LM Studio или Ollama, скачайте чат-модель и запустите локальный сервер. В Настройки → Локальный ИИ выберите провайдера, адрес и модель, затем сохраните. Начните с рекомендованных настроек.",
      ),
    ],
    [
      t("Check web search", "Проверьте веб-поиск"),
      t(
        "Open Settings → Web search, select engines and check their availability. Internet access is required; free search services may rate-limit requests.",
        "Откройте Настройки → Веб-поиск, выберите поисковики и проверьте доступность. Нужен интернет; бесплатные сервисы могут ограничивать частоту запросов.",
      ),
    ],
    [
      t("Start with what you know", "Начните с известных сведений"),
      t(
        "Enter a name and useful context, such as a university, organisation or public work. Set a modest budget, create the research, then start it explicitly.",
        "Введите имя и полезный контекст: университет, организацию или публичную работу. Задайте небольшой бюджет, создайте исследование и отдельно запустите его.",
      ),
    ],
    [
      t("Review, refine, export", "Проверьте, уточните, сохраните"),
      t(
        "Read source quotations before accepting a match. Add clues with Refine & continue. Export the report or the whole project when you need a portable copy.",
        "Прочитайте цитаты перед подтверждением совпадения. Добавьте ориентиры через Уточнить и продолжить. Скачайте отчёт или весь проект, когда нужна переносимая копия.",
      ),
    ],
  ];
  return (
    <article className="welcome-page">
      <section className="welcome-hero">
        <div className="eyebrow">
          <span />
          LOCUS · {t("GETTING STARTED", "ЗНАКОМСТВО")}
        </div>
        <h1>
          {t("A name is a starting point.", "Имя — начало исследования.")}
        </h1>
        <p className="welcome-lead">
          {t(
            "Explore public profiles and mentions with local AI. Turn a search into an organised project you can inspect, refine and keep.",
            "Исследуйте публичные профили и упоминания с локальным ИИ. Собирайте результаты в понятный проект, который можно проверить, уточнить и сохранить.",
          )}
        </p>
        <div className="welcome-actions">
          <button className="button primary" onClick={start}>
            {t("Open workspace", "Открыть рабочее пространство")}
            <ArrowRight size={17} />
          </button>
          <button className="button secondary" onClick={settings}>
            {t("Set up local AI", "Настроить локальный ИИ")}
          </button>
        </div>
        <p className="welcome-caption">
          {t(
            "Early release · Local inference · No paid search API required",
            "Ранняя версия · Локальный ИИ · Без обязательных платных поисковых API",
          )}
        </p>
      </section>
      <section aria-labelledby="welcome-features">
        <h2 id="welcome-features">
          {t("What makes Locus useful", "Чем полезен Locus")}
        </h2>
        <div className="welcome-grid">
          {features.map(([Icon, title, body]) => (
            <div className="welcome-feature" key={title}>
              <Icon size={21} aria-hidden="true" />
              <h3>{title}</h3>
              <p>{body}</p>
            </div>
          ))}
        </div>
      </section>
      <section className="welcome-steps" aria-labelledby="welcome-start">
        <div>
          <div className="eyebrow">01 — 04</div>
          <h2 id="welcome-start">
            {t("Your first research", "Первое исследование")}
          </h2>
          <p>
            {t(
              "No search starts just by opening Locus. You choose when the model works.",
              "Открытие Locus не запускает поиск. Вы решаете, когда модель работает.",
            )}
          </p>
        </div>
        <ol>
          {steps.map(([title, body]) => (
            <li key={title}>
              <h3>{title}</h3>
              <p>{body}</p>
            </li>
          ))}
        </ol>
      </section>
      <section className="welcome-faq" aria-labelledby="welcome-know">
        <h2 id="welcome-know">{t("Before you begin", "Что нужно знать")}</h2>
        <details>
          <summary>{t("What stays local?", "Что остаётся локальным?")}</summary>
          <p>
            {t(
              "Model inference and the project database stay on your computer when using a truly local model server. Search queries go to the selected search services; visited sites receive page requests. Locus has no telemetry. Local research files are not encrypted by Locus.",
              "При использовании действительно локального модельного сервера ИИ и база проектов работают на вашем компьютере. Поисковые запросы отправляются выбранным поисковикам; сайты получают запросы страниц. Телеметрии в Locus нет. Сам Locus не шифрует файлы исследований.",
            )}
          </p>
        </details>
        <details>
          <summary>
            {t(
              "Does a match mean the person is identified?",
              "Совпадение означает, что человек найден?",
            )}
          </summary>
          <p>
            {t(
              "No. The evidence meter describes support for your known clues after quote validation and a separate semantic review by the local model. The model can still misread a source. The report separates checked findings, unresolved questions and unavailable pages; it does not give a calibrated probability of identity. Confirmed cards can form a sourced overview of public work and education.",
              "Нет. Шкала показывает поддержку ваших ориентиров после проверки цитат и отдельной смысловой проверки локальной моделью. Модель всё ещё может неверно прочитать источник. В отчёте разделены проверенные сведения, открытые вопросы и недоступные страницы; статистической вероятности личности он не даёт. Подтверждённые вами карточки образуют обзор публичной деятельности и образования по источникам.",
            )}
          </p>
        </details>
        <details>
          <summary>
            {t(
              "Can it search every website and social network?",
              "Можно искать по всем сайтам и соцсетям?",
            )}
          </summary>
          <p>
            {t(
              "Coverage depends on search indexes and accessible public HTML pages. Private profiles, login walls, blocked pages and pages that require JavaScript may be unavailable. There are no direct Facebook, LinkedIn, VK or OK connectors yet. Missing results do not prove that no profile exists.",
              "Охват зависит от поисковых индексов и доступных публичных HTML-страниц. Закрытые профили, страницы со входом, блокировками или обязательным JavaScript могут быть недоступны. Прямых подключений Facebook, LinkedIn, VK и OK пока нет. Отсутствие результатов не доказывает отсутствие профиля.",
            )}
          </p>
        </details>
        <details>
          <summary>
            {t(
              "Will it run on 8 GB of memory?",
              "Будет работать с 8 ГБ памяти?",
            )}
          </summary>
          <p>
            {t(
              "A compact model with a short context may work, but Locus has not been validated on 8 GB hardware. Model choice affects extraction and planning quality. A dedicated low-memory profile and comparative accuracy benchmarks are still planned.",
              "Компактная модель с коротким контекстом может работать, но Locus ещё не проверен на компьютере с 8 ГБ. Выбор модели влияет на качество извлечения и планирования. Специальный экономный профиль и сравнительные испытания точности пока в планах.",
            )}
          </p>
        </details>
        <details>
          <summary>
            {t("How do I share the app?", "Как поделиться приложением?")}
          </summary>
          <p>
            {t(
              "Share a clean source-code ZIP or invite someone to the private GitHub repository. They install Python, Node.js and a local model provider and run their own copy. Your localhost address works only on your computer. Use the included START-HERE guide; do not send your data folder as part of the app.",
              "Передайте чистый ZIP исходников или пригласите человека в приватный репозиторий GitHub. Он устанавливает Python, Node.js и провайдер локальной модели и запускает свою копию. Ваш адрес localhost работает только на вашем компьютере. Инструкция лежит в START-HERE; папку data вместе с программой не отправляйте.",
            )}
          </p>
        </details>
      </section>
      <footer className="welcome-footer">
        <p>VibeCoded by Sergey Yemelin</p>
        <p>
          {t(
            "Built and reviewed with ChatGPT 6 Astra. Early software: review is not a guarantee of accuracy or security.",
            "Создано и перепроверено с ChatGPT 6 Astra. Ранняя версия: проверка не гарантирует точность или безопасность.",
          )}
        </p>
      </footer>
    </article>
  );
}
