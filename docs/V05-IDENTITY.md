# Identity criteria engine — 0.5

## Problem and contract

Previously city, country and birth-year range guided query planning but did not govern the evidence score. Strong professional clues could hide missing geography, while all non-rejected namesakes appeared in the default list. This release separates discovery from eligibility.

A candidate is eligible only when its reviewed source supports the name and **every supplied dedicated criterion**. Each criterion has three states: supports, unknown, contradicts. Unknown is neither a match nor disproof. An empty criterion imposes no requirement. Structured school, organization and public-work entries are also mandatory; uncertain suggestions belong in free-text context, which remains a planning hint.

## Implemented pipeline

1. Generate candidate queries with local AI. Preserve the original supplied city and country in every planned or previously queued query. Enforce existing name checks, deduplication and budgets.
2. Retrieve public source URLs. Name and geographic mentions in search snippets affect reading priority only; they never become evidence.
3. Fetch accessible pages and extract candidate claims with literal quotations.
4. Separately review claim attribution and required criteria with the local model. Geography must refer to this person and the same place, including region/country qualifiers. A footer, a different person, a country domain or a website language is insufficient.
5. Validate quoted checks against fetched text and supplied excerpts. Geographic and year quotations must contain the candidate's full name and the observed value. A supported geographic relation additionally requires the model's same-place judgment. Birth years must occur in birth-related text; numeric range comparison is deterministic. A different current location alone becomes unknown, not contradictory; geographic contradictions require an explicit denial mentioning the requested place.
6. Compute the all-criteria gate independently of the old evidence score. Missing or stale checks cannot be offset by several professional clues. Contradictions and unknown links are separate UI groups. Manual confirmation does not silently override unmet criteria.
7. Give missing criteria back to the planner. For a named unresolved record, try a source-scoped query with geographic anchors to investigate the missing connection. Do not spend follow-up budget elaborating a rejected or contradictory record. Review work is prioritized before further fetching.
8. Exclude unresolved/conflicting records from the combined profile and reviewed-claim conclusion. Reports preserve them as explicitly labelled leads with source links, without presenting their biographies as matching profiles.

Country selection also controls default search-region behavior: Ukraine keeps its region even for English queries; another supplied country avoids silently defaulting to a US region. Explicit region settings win.

## Evidence, not a percentage

A search engine retrieves possible records; an identity decision is a separate step. This distinction is established record-linkage practice, rather than a claim of a newly invented scientific algorithm. [Splink's official blocking tutorial](https://moj-analytical-services.github.io/splink/demos/tutorials/03_Blocking.html) explains the retrieval-versus-comparison tradeoff. Locus does not use Splink or a trained probabilistic linkage model in this release.

No statistical identity percentage is shown. The synthetic tests exercise particular failure modes; they do not measure population accuracy, recall, or superiority over other products. Rechecking with the same model is not independent corroboration.

## Limits and next work

- Matching is conservative and page-based. Separate cards are not automatically merged, and evidence distributed across several pages may fail the all-criteria gate. A future evidence graph needs independently defensible links between records, not name equality.
- Geographic equivalence and attribution still depend on the model. There is no authoritative geographic-ID resolver yet. Quotation checks prove text presence, not its truth or the correctness of the model's interpretation.
- Original geographic anchors can reduce multilingual retrieval recall. A next iteration should resolve city/region/country IDs and verified historical/transliterated aliases before query generation, while keeping unresolved homonyms separate.
- Full-name quotations reject some legitimate pronoun-based or abbreviated sources. Birth-context checks are deliberately limited and can still misinterpret complex sentences containing several years.
- City currently means a biographical connection, including a past connection. Explicit origin/current residence/study place and time intervals would improve relation matching; this release does not infer private residential addresses.
- Free-text context is not automatically converted into hard constraints. There is no calibrated 8 GB quality profile or benchmark against commercial services.
- Real improvements should be measured on consented or fictional labelled examples: same-name negatives, similarly named cities in different countries, moves, missing data, conflicting dates and multilingual variants. Track false positive rate and recall separately, plus source coverage and unresolved rate.

## Compatibility and validation

Database schema remains 4. Audit method changes to `criteria-review-v3`; previous audits are not reused for current eligibility. Saved records and manual decisions remain in history. Existing pending queries are anchored at execution. New auditing happens only after an explicit start/continue; app launch does not trigger inference.

See [validation](VALIDATION.md) for the measured test results. Public, non-sensitive professional, education and publication research remains the scope. No private contact discovery, family dossiers, leaked databases, face identification or login bypass is added.
