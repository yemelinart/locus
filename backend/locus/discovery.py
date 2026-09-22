"""Diverse retrieval hypotheses. None of these queries constitute identity evidence."""

import re
from urllib.parse import urlsplit

from .identity import normalized
from .models import Query
from .names import RUS, UKR, variants
from .verification import useful_query


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
    anchors = [*place_spellings(brief.city), *[c.text for c in brief.evidence_clues[:3]]]
    if not anchors:
        anchors = [brief.country] if brief.country else []
    result = []
    # Interleave names and clues instead of exhausting a single spelling first.
    for i, name in enumerate(names):
        language = brief.languages[i % len(brief.languages)]
        if anchors:
            result.append(
                Query(
                    query=f"{quoted(name)} {quoted(anchors[i % len(anchors)])}",
                    language=language,
                    reason="Discover using a name and contextual clue",
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


def portfolio(brief, planned, previous, limit, first_round=False):
    """Bounded diverse candidates, including at most two broad probes per first round."""
    if limit <= 0:
        return []
    seen = {normalized(x) for x in previous}
    seeds = seed_queries(brief) if first_round else []
    # Deterministic seeds survive an empty or poor model plan; later rounds remain adaptive.
    choices = []
    for i in range(max(len(seeds), len(planned))):
        if i < len(seeds):
            choices.append(seeds[i])
        if i < len(planned):
            choices.append(planned[i])
    result = []
    for query in choices:
        key = normalized(query.query)
        if key in seen or not useful_query(query, brief):
            continue
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
        else:
            term = quoted(term)
        queries.append(
            Query(
                query=f"{name} {term}",
                language=brief.languages[0],
                reason=f"Investigate missing criterion: {check['field']}",
            )
        )
    if host:
        queries.append(
            Query(
                query=f"{name} site:{host}",
                language=brief.languages[0],
                reason="Find related public profile pages on the observed source",
            )
        )
    return queries[:4]
