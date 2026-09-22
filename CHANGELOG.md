# Changelog

## 0.5.0 — 2026-09-21

- Required city, country, birth-year and structured-clue gates with quoted supports / unknown / contradictions. Namesakes without all supplied criteria are separated from matching results and report biographies.
- Conservative same-person, same-place and birth-year checks; another current location alone is not an explicit contradiction. Previous audits become stale without deleting records.
- Geography-preserving planned and queued queries; missing-link follow-ups, snippet reading priority and target-country search-region defaults.
- Bilingual criterion explanations, dedicated unresolved/conflict filters and an opt-in synthetic local-model identity harness. Schema remains 4.

## 0.4.0 — 2026-09-21

- Added durable real-phase activity and an animated research observatory, with observed source domains, paused state, animation toggle and reduced-motion support.
- Added a separate local semantic-review queue. Claim attribution, clue relations and exact citations are validated before statements enter the profile overview. Invalid IDs, duplicates and unsupported statements fail closed.
- AI observations cite accepted claim indices and receive a further local check against only those claims before appearing in the research view and journal. Unsupported details and identity assertions are withheld. Reports distinguish partial findings, missing support and source-access failures, and combine only user-confirmed cards into a public-work overview.
- Relevant source windows can include mentions near the end of a long page. Planned and follow-up queries must include a target-name hypothesis (or an explicit public clue with a first name for surname changes).
- Schema 4 adds versioned candidate audits and worker activity. Databases from schemas 1–3 are backed up. Legacy and revised cards lose semantic support until checked on the next explicit start; pause/retry preserves cards.
- Added adversarial deterministic fixtures and an opt-in eight-case local-model smoke harness. No identity-probability calibration, automatic photo collection or independent verification claim.

## 0.3.2 — 2026-09-21

- Added a bilingual first-visit introduction and reusable About & guide page, with capabilities, four setup steps and practical limitations. Search form remains separate.
- Added an English product README, retained the Russian reference, and wrote first-run, update and private-sharing guides.
- Setup now checks prerequisites before installing dependencies. Source releases exclude personal research and local runtime files.

## 0.3.1 — 2026-09-21

- Выбор LM Studio, Ollama или другого локального OpenAI-compatible сервера с редактируемым адресом и списком моделей.
- Нативный Ollama API: metadata-only discovery, параметры генерации, JSON Schema и поддерживаемые режимы thinking. Удалённые/cloud-модели блокируются перед передачей задания.
- Мини-гайд параметров генерации, пояснения подключения и рекомендация сохранять исходные значения без конкретной причины.
- Рекомендации ИИ и веб-поиска разделены; смена адреса/провайдера сбрасывает несовместимые режимы, поздние ответы старой проверки игнорируются.
- Обратная совместимость сохранённых настроек: по умолчанию LM Studio. Схема базы не меняется.

## 0.3.0 — 2026-09-21

- Шкала обоснованности совпадения с объяснениями и цитатами; без вымышленных процентов вероятности.
- Структурированные ориентиры: образование, организация, публикация/публичная работа.
- Продолжение того же исследования с редактированием критериев, дополнительным бюджетом и новым планом; история версий и предыдущих оценок.
- Исключённые доменными фильтрами карточки остаются в архиве и возвращаются при снятии фильтра. Прежние ручные оценки требуют повторной проверки.
- Локальная папка проекта, безопасный офлайн HTML и ZIP с PDF/Markdown/JSON, выдержками, ссылками и историей. Удаление исследования удаляет папку.
- Схема SQLite 3; автоматическое резервное копирование схем 1/2 перед переносом. Существующие данные сохранены.
- Публичные профессиональные сведения остаются границей проекта; сбор семейного досье и фотографий частных людей не добавлен.

## 0.2.0 — 2026-09-21

- English по умолчанию, русский, общий каталог переводов интерфейса и отчётов.
- Четыре палитры и три уровня яркости, сохранение предпочтений.
- About: VibeCoded by Sergey Yemelin; Built and rechecked with ChatGPT 6 Astra.
- PDF с локально встроенными шрифтами Noto Sans (OFL), структурированные Markdown и JSON.
- Анализ исследования и действия удаления/экспорта рядом с поисками в истории.
- Прежние имена, возможная смена фамилии, предпросмотр гипотез транслитерации.
- Динамические capabilities LM Studio, нативный thinking и параметры генерации.
- Фактический каталог адаптеров DDGS, проверка подключения, SafeSearch, регион и рекомендации.
- Чередование движков, одна резервная попытка, запись реальных обращений.
- Миграция SQLite 1 → 2 с предварительной резервной копией; старые исследования сохраняются.
- Проверки переводов, тем, экспорта, миграции и возможностей моделей.


## 0.1.0 — 2026-09-21

- Первая локальная версия: интерфейс, SQLite, долговечная очередь и один исполнитель.
- LM Studio / локальный OpenAI-compatible API; облачные адреса отключены.
- Совместимый режим Qwen 3 без длинного thinking, не меняющий файлы модели.
- Контрольная точка времени каждые пять секунд.
- Прямой бесплатный метапоиск и адаптер локального SearXNG.
- HTML reader с robots.txt, проверкой адресов, DNS и перенаправлений.
- Проверка присутствия цитат, отдельные кандидаты и ручная оценка совпадений.
- Бюджеты, пауза, продолжение, уточнения, история и экспорт.
- Модульные и интеграционные тесты, браузерные сценарии, документация архитектуры.
