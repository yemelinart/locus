# Changelog

## 0.7.0 — 2026-09-22

- Weak nonempty search results can trigger another selected index. Canonical URL deduplication and name/place/school signals rank discovery results; snippets never establish identity.
- Source excerpts prioritize coverage of requested criteria and nearby name mentions instead of spending the entire context on repeated names near the start of a page. Literal passages remain separated across omissions.
- The identity reviewer can select numbered exact source passages instead of retyping quotations. This fixes rejected ellipsis-shortened evidence without bypassing subject, place, year or literal-source checks. Birth-year-only searches also guide retrieval; contradictory years remain visible to the reviewer.
- Missing-criterion probes rotate across city, country, year and structured clues. Previously scheduled probes are removed before the next bounded batch is selected.
- Restored bounded navigation to explicitly named professional profiles/portfolios, fixing a 0.6.3 regression in split-source evidence discovery. No automatic identity merge.
- Malformed/schema-invalid model output gets one bounded retry. Repeatedly invalid extraction/review steps are retained for explicit resumption while other paths proceed; three consecutive failed steps pause the run. Failed optional commentary does not erase the core review. Pending retries are shown in conclusions and exports.
- Preserved article headings and short public profile text; recognized selected HTTP-200 access-check pages as unreadable. Rejected multicast source URLs and DNS answers.
- Added a seven-case closed-corpus quality suite to CI, including explicit negative cases. No new dependency, schema migration or audit invalidation. Existing reviewed records are retained; improved processing applies to newly executed steps.

## 0.6.3 — 2026-09-22

- Removed the unconditional “Possible match” card label and positive name-only evidence bar. Unreviewed records, unconfirmed identity, conflicting criteria and supported criteria now have separate labels in the interface and exports.
- Applied the model's validated identity decision before expanding observed source links. Unconfirmed records get at most two biography/profile leads, not automatic enumeration of a namesake's works. Eligible records retain bounded public-source expansion.
- Existing unconfirmed expansion tasks are deferred without reading the page; they remain recoverable if later criteria or confirmed source links establish the connection. Explicit seed URLs, URL deduplication, depth limits and shared budgets remain in force.
- Collapsed proposed source links by default. Descriptions of unconfirmed people are explicitly separated from facts about the research target.
- Schema and audit method unchanged. These are presentation and navigation fixes, not evidence of higher real-world recall or competitor superiority.

## 0.6.2 — 2026-09-22

- Fixed Resume silently requeueing an exhausted search. Completed/blocked passes now open an explicit next-pass allowance dialog; the API rejects an exhausted direct start.
- Continuing unchanged criteria preserves the revision, audits, manual decisions, queue and query/URL deduplication. Actual criteria changes still trigger reassessment.
- Added a monotonic live clock with second-by-second display independent of activity writes and polling; prevented overlapping/stale poll responses across actions.
- Prioritized missing-criterion probes and source-specific city checks. Later passes can explore unused spelling hypotheses without repeating completed queries.
- Exposed the active AI/web role, saved queue and latest identity check, including missing or conflicting criteria. Optional narrative validation has its own visible stage.
- Schema remains 5. No automatic search restart, no new model provider or inference mode, no change to match-acceptance gates.

## 0.6.1 — 2026-09-22

- Fixed empty ddgs responses being treated as connection failures and prematurely pausing research.
- Added an attributed offline GeoNames/CLDR place reference. Required city/country matches now receive a deterministic check independent of the model's same-place verdict; ambiguous locations stay unresolved.
- Recognize reversed full names and bounded Slavic patronymics; preserve name tokens and reject candidate-name substitutions. Added Alexey/Oleksii hypotheses.
- Normalize malformed search quotation marks, cap unanchored planning queries, use geographic aliases in retrieval and investigate missing criteria before namesake biography expansion.
- Review method v4 invalidates older assessments until explicit resume. Database schema stays 5; no automatic search restart.
- Checkpoint the core identity/claim review before optional narrative generation, so a cancelled or timed-out observation cannot erase the useful result.
- Added regression cases, an unseeded public-target discovery harness and a candid market/product audit. No comparative reliability or market-superiority claim.

## 0.6.0 — 2026-09-21

- Separated diverse retrieval hypotheses from mandatory result criteria. Added bidirectional name variants and missing-criterion queries; removed automatic addition of all original geographic phrases to every query.
- Preserved public, name-scoped hyperlinks and Person sameAs declarations as navigation leads, with bounded following, domain/robots/URL checks and shared page budgets. Redirect aliases retain source provenance.
- Added explicit user decisions for proposed source links and combined criterion evidence across confirmed records. Source cards remain separate; contradictory, rejected, excluded or stale evidence cannot silently strengthen a group. Reports include combined evidence with citations.
- Interleaved query families after two page reads, prioritized less-explored hosts, added search-adapter cooldowns and revision-scoped empty-page analysis.
- Schema 5 adds observed source links, redirect aliases and versioned link decisions; earlier schemas are backed up. No automatic inference on startup.
- Added engine replay, local-model and public-web smoke harnesses, regression tests and a product audit. No market ranking or statistical accuracy claim.

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
