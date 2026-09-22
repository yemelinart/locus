# Search audit and competitive assessment — 2026-09-22

## Product verdict

Locus has a useful potential niche: free local-model research from a name and
remembered biographical context, with saved projects and explicit namesake
separation. It has **not demonstrated reliable identification of ordinary people
or superiority to commercial services**. Successful unit tests do not establish
that. A city is a required biographical connection, including earlier life; a
different current city is not a disproof.

## Failures reproduced in 0.6.0

1. **Empty retrieval falsely stopped research.** The pinned ddgs 9.13 raises
   DDGSException("No results found.") for an empty aggregate/ranker output.
   Locus treated this exactly like a failed connection, poisoned adapter health
   and paused after three failed logical queries. Both installed searches were
   paused with that generic error. A neutral live query succeeded; a fictional
   exact-name query reproduced the exception. This demonstrates the bug, but
   historical generic logs cannot prove the cause of every earlier failure.
2. **The model could override geography.** An injected incorrect review claiming
   Moscow/Russia meant the requested Zaporizhzhia/Ukraine passed both geographic
   checks in the unchanged 0.6.0 code. The old validator checked quotation
   presence and model booleans, not actual place equivalence.
3. **Correct names were skipped.** The old preflight did not recognize
   “Алексей Петрович Иванов” for “Алексей Иванов”, or the reversed order.
4. **Malformed and drifting queries.** Saved plans contained literal backslashes
   before quotation marks, as well as unrelated-city exploration. Planning
   prompts alone did not enforce a limit on unanchored queries.

## Delivered mechanism

Name and supplied criteria → bounded contextual discovery → accessible page →
separate candidate → local semantic attribution → deterministic name/place/year
checks → all-criteria acceptance → optional human confirmation/linking.

- Empty ddgs aggregate outputs become empty results and trigger another selected
  adapter, not a connectivity failure. HTTP/DNS/timeout/rate-limit exceptions
  remain errors. An empty result does **not** prove exhaustive coverage or even
  that an HTML adapter parsed the site correctly.
- Offline GeoNames snapshot: 34,146 populated-place records, alternate names,
  country/region identifiers. CLDR supplies EN/RU/UK country names. The requested
  place and observed place are resolved separately. The requested country is
  **never injected into the observed location** to make it match.
- Unknown, ambiguous or incompatible places cannot pass merely because the
  model says same_place=true. Literal country/region qualifiers must occur in
  the evidence. Small unlisted places can use exact full spelling; qualifiers
  are never dropped. Bounded RU/UK inflections are supported.
- Full-name token order and selected Slavic patronymics are recognized.
  A different extracted name cannot become compatible just because a paragraph
  also mentions the target. Added Alexey/Oleksii language hypotheses.
- Search spelling hypotheses come from the place reference; homonymous aliases
  receive the supplied country in discovery queries when it resolves ambiguity.
  At most two unanchored model/seed queries per planning round. Unknown city
  connections produce targeted follow-ups before general biography expansion.
- Legacy research gets up to four new contextual probes on an explicit resume,
  within remaining budgets. No auto-resume or user-data deletion.
- The completed identity/claim audit is saved before optional narrative
  generation; a narrative timeout can no longer erase the core review.

No new database schema: schema remains 5. Review method advances to
criteria-review-v4; older audits become pending until explicit research resume.
The local gazetteer is packaged with the application and makes no runtime
GeoNames request. The code remains MIT; third-party geographic data has its
own attribution notices in backend/locus/geodata.

## Market comparison

This is a comparison of documented workflows, **not a comparative accuracy
benchmark**, and no paid reports were purchased.

| Product | What its documented approach offers | Implication for Locus |
| --- | --- | --- |
| [Sherlock](https://github.com/sherlock-project/sherlock) | Free MIT tool for checking usernames across social sites. | Useful if a username is already known. The documented input is not name + former city. |
| [Maigret](https://github.com/soxoj/maigret) | Free MIT username research, extraction, recursive discovered identifiers, web UI and reports; optional AI analysis. | Free research and AI summaries are not unique to Locus. Maintained source adapters and observed-link discovery matter. |
| [Maltego](https://www.maltego.com/blog/how-to-conduct-person-of-interest-investigations-using-osint-and-maltego/) | Graph-based investigation, multiple data integrations, and pivots between found entities and sources. | The useful lesson is following established relationships. Locus has a much smaller integration set; its breadth is not comparable today. |
| [Whitebridge](https://whitebridge.ai/) | Markets consolidated person reports and 100+ public sources; self-service reports are paid. Its own page disclaims completeness and guaranteed accuracy. | A paid polished report is not proof of better identity resolution; equally, Locus has no evidence that it beats it. |

Using search engines for discovery is reasonable. An LLM does not provide a
web index or access to material that sources do not expose. Locus's useful
additional work must be checking who each result describes, testing missing
biographical relationships, preserving separate hypotheses, and producing a
readable public profile after those checks.

## Remaining critical work, in priority order

1. **Representative evaluation.** Build a consented/labeled set including sparse
   profiles, common names, RU/UK/Latin variants, moves and genuinely unfindable
   cases. Compare against manual name+city search under a fixed time budget.
   Measure wrong-person acceptance, verified target discovery, abstention,
   supported biography coverage and time/cost. Keep held-out cases.
2. **Attribution across paragraphs.** The full-name-in-quote guard still misses
   ordinary biographies that name someone in a heading and use pronouns below.
   Safely recovering those relations needs explicit document subject boundaries
   and adversarial evaluation. A place dictionary does not solve this.
3. **Source access and efficient retrieval.** Some social sites need login,
   disallow automation or expose little readable HTML. PDF/rendered-page
   coverage and adapter monitoring remain incomplete. Noise from engines that
   ignore exact queries still costs page budget.
4. **Structured biographical relationships.** The city field currently means
   any relevant past/present connection. “Lived in”, “studied in”, dates and
   region disambiguation should become explicit, user-reviewable relationships.
   Free-text context currently guides planning; it is not automatically a set
   of mandatory criteria.
5. **Person-oriented output.** A coherent profile and chronology, with public
   accounts and clear unknowns, must become the result users read. Source
   quotations should stay accessible underneath. Separate source cards are
   still too prominent; this audit does not pretend that UX is solved.

These changes improve specific failure modes. They are not a new scientific
entity-resolution algorithm, calibrated identity probabilities, full internet
coverage, or a guarantee that a particular person can be found.
