"""Diverse retrieval hypotheses. None of these queries constitute identity evidence."""

import re
from urllib.parse import urlsplit

from .identity import normalized
from .models import Query
from .names import RUS, UKR, variants
from .places import resolve, search_spellings
from .verification import useful_query

DISCOVERY_TAG = "Context discovery v2"


def quoted(value):
    return '"' + value.replace('"', " ").strip() + '"'


def place_spellings(value):
    """Bounded transliteration hypotheses, not a geographic resolver."""
    values = [value.strip()]
    if re.search("[а-яёіїєґ]", value, re.I):
        for mapping in (RUS, UKR):
            values.append("".join(mapping.get(c, c) for c in value.lower()))
    return list(dict.fromkeys(v for v in values if v))


def seed_queries(brief):
    options = variants(brief)
    names = [n["name"] for n in options if n["origin"] == "supplied"][:8]
    given = {normalized(name.split()[0]) for name in names}
    for item in options:
        first = normalized(item["name"].split()[0])
        if first not in given and len(names) < 8:
            names.append(item["name"])
            given.add(first)
    for item in options:
        if item["name"] not in names and len(names) < 8:
            names.append(item["name"])
    anchors = [*search_spellings(brief.city, brief.country), *[c.text for c in brief.evidence_clues[:3]]]
    if not anchors:
        anchors = [brief.country] if brief.country else []
    result = []
    # Interleave names and clues instead of exhausting a single spelling first.
    for i, name in enumerate(names):
        language = brief.languages[i % len(brief.languages)]
        if anchors:
            anchor = anchors[i % len(anchors)]
            qualifier = (
                " " + quoted(brief.country)
                if brief.country and len(resolve(anchor)) > 1 and len(resolve(anchor, brief.country)) == 1
                else ""
            )
            result.append(
                Query(
                    query=f"{quoted(name)} {quoted(anchor)}{qualifier}",
                    language=language,
                    reason=DISCOVERY_TAG + ": name and biographical clue",
                )
            )
        if i < 2:
            result.append(
                Query(
                    query=quoted(name),
                    language=language,
                    reason="Broader discovery; all identity criteria still required",
                )
            )
    return result


def contextual(query, brief):
    anchors = [
        *search_spellings(brief.city, brief.country),
        brief.country,
        *[c.text for c in brief.evidence_clues],
    ]
    return any(normalized(a) in normalized(query.query) for a in anchors if a.strip())


def portfolio(brief, planned, previous, limit, first_round=False):
    """Bounded diverse queries; at most two unanchored probes per planning round."""
    if limit <= 0:
        return []
    seen = {normalized(x) for x in previous}
    seeds = seed_queries(brief)
    # Keep unused spelling/clue hypotheses available in later passes too. Completed
    # queries are removed below; a resumed run must never recycle its first batch.
    choices = []
    for i in range(max(len(seeds), len(planned))):
        if i < len(seeds):
            choices.append(seeds[i])
        if i < len(planned):
            choices.append(planned[i])
    result = []
    broad = 0
    has_context = bool(brief.city.strip() or brief.country.strip() or brief.evidence_clues)
    for query in choices:
        key = normalized(query.query)
        if key in seen or not useful_query(query, brief):
            continue
        if has_context and not contextual(query, brief):
            if broad >= 2:
                continue
            broad += 1
        seen.add(key)
        result.append(query)
        if len(result) >= limit:
            break
    return result


def verification_queries(brief, candidate, page_url, checks):
    """Test a missing relation rather than repeatedly appending all constraints."""
    name = quoted(candidate["name"])
    host = urlsplit(page_url).hostname
    queries = []
    for check in checks:
        if check["relation"] != "unknown":
            continue
        term = check["requested"]
        if check["field"] == "birth_year":
            term = "born biography"
        elif check["field"] == "city":
            if host:
                queries.append(
                    Query(
                        query=f"{name} {quoted(brief.city)} site:{host}",
                        language=brief.languages[0],
                        reason="Investigate missing criterion: city on the observed source",
                    )
                )
            for place in search_spellings(brief.city, brief.country)[:3]:
                queries.append(
                    Query(
                        query=f"{name} {quoted(place)}",
                        language=brief.languages[0],
                        reason="Investigate missing criterion: city",
                    )
                )
            continue
        else:
            term = quoted(term)
        queries.append(
            Query(
                query=f"{name} {term}",
                language=brief.languages[0],
                reason=f"Investigate missing criterion: {check['field']}",
            )
        )
    if host and not any(c["relation"] == "unknown" for c in checks):
        queries.append(
            Query(
                query=f"{name} site:{host}",
                language=brief.languages[0],
                reason="Find related public profile pages on the observed source",
            )
        )
    return queries[:4]
