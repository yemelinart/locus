# Locus

### A name is a starting point.

**Research public profiles and mentions with local AI. Keep the sources, refine the search, own the project.**

[Start here](START-HERE.md) · [Русский](README.ru.md) · [Sharing & private GitHub](docs/SHARING.md) · [Changelog](CHANGELOG.md)

Locus turns a name and a few known details into a research workspace. Your local model plans multilingual queries and extracts source-backed observations from accessible public pages. You review possible matches, add clues and continue the same project as your understanding improves.

**0.6.2 · Early release · MIT-licensed code · Local web app**

## New in 0.6.2

Resume now explains exhausted limits and offers a fresh allowance for the next pass. Continuing unchanged criteria keeps the queue, reviews and visited-page history. The live timer ticks in seconds; the process panel separates local AI work from web requests and shows the latest identity decision, including missing links. Missing-criterion queries get priority over generic discovery.

[Continuation, timing and search-quality roadmap](docs/V062-CONTINUATION.md). These changes improve run control; broad people-finding accuracy remains unproven.

## New in 0.6.1

Fixed empty web results incorrectly stopping research as a connection failure.
An offline place reference now checks city/country equivalence separately from
the local model. Name-order/patronymic handling and contextual queries were
improved. Older assessments wait for re-review on an explicit resume.
See the [engine and market audit](docs/V061-SEARCH-AUDIT.md) for reproduced
failures, the comparison with existing tools and the work still needed.
Place data has [separate attribution](backend/locus/geodata/README.md).

## New in 0.6

The engine now separates broad discovery from strict result eligibility. It uses name-and-context query families, bidirectional Cyrillic/Latin spelling hypotheses and observed hyperlinks to find additional source pages. Retrieval can omit a criterion while the final match must still satisfy every supplied criterion.

Locus proposes connections between source cards when it observes a name-scoped link. Review the source context and explicitly confirm that the records describe the same person. Only then can complementary criteria from different pages form a combined profile. Quotes retain their source references; conflicts, stale reviews and rejected cards cannot silently produce a positive result. Decisions can be undone. HTML links are navigation leads, not identity proof.

The worker interleaves query results, favors less-explored hosts and temporarily avoids repeatedly failing search adapters. Old empty extractions can be reconsidered after criteria revision. SQLite schema 5 is backed up before migration. Previously saved pages retain their old snapshots; hyperlinks are available on newly read pages.

[Product audit, implementation plan and honest limitations](docs/V06-PRODUCT-AUDIT.md) · [Engine architecture](docs/V06-ENGINE.md)

## Earlier: 0.5

City, country, birth-year range and structured public clues are now required matching criteria. Each is supported, unknown or contradicted, with a source quotation. Only records meeting every supplied criterion appear in the default results. Unverified connections and conflicts have separate filters; a namesake alone does not count as a match. A different current city does not disprove a past connection.

The planner receives missing criteria, follow-up searches target missing connections, and every executed query retains the entered city and country. Search snippets affect reading order only. Reports exclude unresolved biographies from the matching profile overview. Existing records remain saved but need the new audit on an explicit Continue. Opening the app does not run AI.

This conservative, page-based check can miss valid people whose evidence is spread across pages. Geographic interpretation remains model-dependent; no calibrated probability or accuracy claim is made. Free-text context guides planning, whereas dedicated fields control matching. See [identity engine design and limitations](docs/V05-IDENTITY.md).

## Earlier: 0.4

The research view now shows an animated observatory driven by the actual worker phase and source URLs. Motion pauses with the research and respects reduced-motion preferences.

After extraction, a separate local-model pass checks whether each quotation supports the claim about the candidate. Invalid references, unsupported or unclear statements stay out of the profile overview. Each reviewed card explains matching clues and potential contradictions; missing data is not a contradiction. A custom AI observation includes references to reviewed claims. Overall conclusions distinguish unreadable sources, insufficient evidence, partial findings and promising candidates. Manually confirmed cards can form a sourced overview of public work and education.

This is a second pass by the same model, not independent corroboration. It still requires human review. Schema 4 backs up earlier databases; existing cards need semantic review on the next explicit research start. Full biography generation, automatic photo collection and identity probability percentages are not provided. Photos, if present, can be checked manually on original profile pages.

## Why use Locus?

- **Choose your own local AI.** LM Studio, Ollama or a compatible local server. Model selection, generation controls and supported reasoning settings are available in the app.
- **Inspect the evidence.** Saved claims include quotations checked against fetched text and links to their sources. Candidate records remain separate for your review.
- **Work across languages.** Queries in 12 supported languages, name variants and former names, with context such as education, organisations and public work.
- **Control the search.** Select free search engines, include or exclude sites, and set limits for time, queries, pages and planning rounds. Pause and continue explicitly.
- **Keep a continuing project.** Refine criteria, add clues, inspect activity and source coverage, and preserve revision history.
- **Take the results with you.** Structured PDF and Markdown reports, JSON data and a project ZIP with an offline report and source excerpts.
- **Make it comfortable.** English and Russian, four palettes and three brightness levels. No Locus account, telemetry or required paid search API.

These are product capabilities, not a claim of superiority. Search accuracy, recall and performance have not been benchmarked against commercial services.

## Start on your Mac

This is currently a source distribution, **not a signed macOS `.app` or a one-click installer**.

1. Install [Python](https://www.python.org/downloads/) 3.11–3.14 (3.12 recommended), [Node.js](https://nodejs.org/en/download) 22.12+ or a supported newer version, and [LM Studio](https://lmstudio.ai/) or [Ollama](https://ollama.com/). Download a chat model in that provider.
2. Extract the Locus ZIP into a folder you will keep, for example `~/Applications/Locus`. Do not run inside the ZIP.
3. Open **Start Locus.command**. The first run installs dependencies and builds the interface, using an internet connection. Alternatively use the terminal commands below.
4. Open **http://127.0.0.1:8420**. Follow **About & guide**, connect your local model in Settings and check web search availability.
5. Create a research project, review its limits and explicitly start it. Merely opening Locus does not start research.

```sh
./scripts/setup.sh
./scripts/start.sh
```

Keep the server terminal open while working. Pause an active search before closing it. The startup guide has first-run troubleshooting and update instructions: [English](START-HERE.md) / [Русский](START-HERE.ru.md).

## What is local, and what uses the internet?

Model inference uses a server on your computer. The database and research archives are stored in the local `data/` folder. Locus does not send research to a cloud LLM and does not collect telemetry. A custom compatible model server must itself run locally, rather than proxying requests to a cloud service.

Web search needs the internet. Search providers receive your queries, and visited sites receive page requests. Locus does not encrypt the local database itself. Providers and model weights have their own licences; no model weights are included.

## Read the results with care

A quotation supports traceability, not truth or identity. The evidence meter describes reviewed support from supplied clues; it is **not an identity probability**. Review the sources and contradictions before confirming a candidate.

Coverage is limited by search indexes, robots rules and accessible public HTML. Login-only content, blocked pages and JavaScript-dependent content may be unavailable. Direct social-network connectors, PDF/OCR ingestion, a validated 8 GB memory profile and a signed desktop installer are not included in this release.

Locus is for public, non-sensitive professional, educational and publication research. It does not provide private contact discovery, residential addresses, leaked databases or face identification.

## Share and contribute

A private GitHub repository can hold the code and downloadable releases. Access requires an invited GitHub account; the URL alone does not grant access. Every user runs their own local copy. Do not share the working folder or `data/` as an application distribution. See [sharing instructions](docs/SHARING.md).

[Contributing](CONTRIBUTING.md) · [Architecture](docs/ARCHITECTURE.md) · [Validation](docs/VALIDATION.md) · [Roadmap](docs/ROADMAP.md) · [Security](docs/SECURITY.md)

**VibeCoded by Sergey Yemelin.** Built and reviewed with ChatGPT 6 Astra. Review is not a guarantee of correctness or security. Source code is distributed under the [MIT licence](LICENSE).
