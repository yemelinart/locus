# Product audit and engine plan — 0.6

## Verdict on 0.5

Locus runs as a local research workspace, but reliable person discovery is not established. Its UI and engineering tests are not evidence of real search quality. There is no representative labelled evaluation or competitor comparison. No defensible percentage, market ranking, or 100% guarantee exists.

Critical defects:

1. Retrieval overconstrains queries with every original geographic phrase. This loses translated spellings and pages that omit a country even when the person is relevant. Mandatory result criteria must be separate from retrieval strategies.
2. All evidence must coexist on one page. The system cannot use complementary facts across an explicitly linked professional profile and a biography without a principled human-reviewed link.
3. Reader discards hyperlinks, so the engine ignores actual source trails and repeatedly asks general search engines instead.
4. FIFO fetching can consume the page/time budget on one query before other name variants and sources are explored. Search providers rotate blindly through failures.
5. A page with no extraction is not reconsidered after a criteria revision because analysis deduplication is global.
6. No reproducible retrieval-and-resolution evaluation exists. Synthetic model checks cover selected errors only; they do not establish recall.

## Implementation plan and acceptance

- Separate retrieval from eligibility. Add deterministic multilingual/name-and-clue seed strategies and explicit query intent. Permit controlled broader discovery, while retaining every required criterion in the result gate. Audit the actual query and strategy. Test that old city anchors cannot corrupt a translated query and that broad discovery cannot promote a namesake.
- Preserve bounded public page links and their source context. Follow only source-grounded, name-scoped trails with depth and per-page limits, existing domain/robots/SSRF checks and the same page budget. No model-invented URLs, private contacts, account login or bypass.
- Propose links between separate candidate cards only from observed source links; do not infer identity from name equality. Require an explicit user link decision before aggregating evidence. Keep quotes, source IDs, revision and conflicts. A rejected, stale, excluded or conflicting member cannot silently supply a positive match. Test split evidence, unrelated namesakes, rejection, criterion edits, and export.
- Interleave retrieval families and bound same-domain reading. Track provider failure streaks and temporary cooldowns, preserving attempts in the journal. Distinguish inaccessible coverage from a negative result.
- Reanalyse previously empty pages after explicit criteria revision, without automatic inference on startup. Preserve budget, cancellation, recovery and old data.
- Add a reproducible fixed-corpus engine evaluation with expected identities and counterexamples. Report fixture precision/recall separately from local-model smoke checks and real-web coverage. Run a bounded local-model end-to-end check. No competitor superiority claim without equal tasks and labelled results.

## Research and comparison boundaries

Maltego's official person-investigation tutorial demonstrates pivots between entities and sources, including organizational relationships. This supports building observable source trails, not copying its broader data collection scope: https://www.maltego.com/blog/how-to-conduct-person-of-interest-investigations-using-osint-and-maltego/

Whitebridge advertises broad live-source coverage and structured reports but also states data may be incomplete and accuracy is not guaranteed. Its public marketing does not provide sufficient evidence to rank Locus against it; no paid account or comparative test was used: https://whitebridge.ai/

Splink documents the tradeoff between broad candidate generation and downstream matching. Locus is not a trained Splink model; this architectural separation is established practice, not a novel scientific claim: https://moj-analytical-services.github.io/splink/demos/tutorials/03_Blocking.html

SearXNG exposes search parameters and unresponsive engines. It remains a metasearch source, not a replacement for source reading or identity evidence: https://docs.searxng.org/dev/search_api.html

## Deferred research, not implemented promises

An authoritative multilingual place resolver with geographic IDs; relation-specific time intervals; labelled real-world public/consented benchmark; calibrated probabilistic linkage; PDF/OCR and optional rendered pages; measured small-model performance. These need independent datasets, extraction work and evaluation rather than more optimistic prompts. Free local inference cannot create evidence missing from accessible sources.

## Delivered and measured

Implemented: diverse retrieval, bidirectional name hypotheses, bounded source trails, explicit reversible link review, combined criterion evidence with conflicts and provenance, report integration, host diversity, provider cooldowns, empty-page reanalysis and pre-extraction name screening. Schema 5 includes backup/migration. Regression tests and engine replay compare the mechanism with 0.5; local-model and real-web smoke tests are recorded separately.

Still **not established**: high recall for an unknown individual from name/city alone, superior precision or recall versus Google/Whitebridge/Maltego, authoritative geographic normalization, calibrated probabilities, or large-scale throughput. Known public targets and fictional cases are acceptance tests, not representative product validation. These remain explicit limitations.
