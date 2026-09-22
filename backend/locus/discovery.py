"""Diverse retrieval hypotheses. None of these queries constitute identity evidence."""

import re
from urllib.parse import urlsplit

from .identity import normalized
from .models import Query
from .names import RUS, UKR, variants
from .places import resolve, search_spellings
from .verification import useful_query

DISCOVERY_TAG = "Context discovery v2"
COVERAGE_TAG = "Spelling coverage v1"


def coverage_queries(brief, limit=4):
    """Bounded name-only recall probes, before any expensive model interpretation.

    A historical city need not appear on today's professional profile. Required
    criteria still govern acceptance, never this discovery pass.
    """
    options = variants(brief)
    supplied = [n["name"] for n in options if n["origin"] == "supplied"]
    roman_surnames = {
        "".join(mapping.get(c, c) for c in name.split()[-1].casefold())
        for name in supplied
        for mapping in (RUS, UKR)
    }
    latin = [
        n["name"]
        for n in options
        if re.fullmatch(r"[A-Za-z' -]+", n["name"]) and n["name"].split()[-1].casefold() in roman_surnames
    ]
    # Common given-name spellings precede mechanical transliterations; speculative
    # changes to every surname vowel do not consume the first discovery pass.
    common = [
        n["name"]
        for n in options
        if n["name"] in latin and n["reason"] == "Name and transliteration hypothesis"
    ]
    other_script = [
        n["name"]
        for n in options
        if bool(re.search(r"[а-яіїєґ]", n["name"], re.I)) != bool(re.search(r"[а-яіїєґ]", brief.name, re.I))
    ]
    choices = list(dict.fromkeys([brief.name, *common[:1], *supplied[1:3], *latin, *other_script]))[:3]
    result = []
    for name in choices:
        language = "en" if name in latin and "en" in brief.languages else brief.languages[0]
        result.append(
            Query(
                query=quoted(name),
                language=language,
                scope="worldwide",
                reason=COVERAGE_TAG + ": name without geographic restriction",
            )
        )
    # A loose reversed-order probe complements exact phrases and changes no name tokens.
    alternate = next((n for n in choices if n in latin), choices[0])
    if len(alternate.split()) == 2:
        result.append(
            Query(
                query=" ".join(reversed(alternate.split())),
                language=result[choices.index(alternate)].language,
                scope="worldwide",
                reason=COVERAGE_TAG + ": reversed name, unquoted",
            )
        )
    for item in options:
        if item["name"] not in choices:
            result.append(
                Query(
                    query=quoted(item["name"]),
                    language=brief.languages[0],
                    scope="worldwide",
                    reason=COVERAGE_TAG + ": additional spelling",
                )
            )
    return result[:limit]


def planning_findings(detail):
    """Unverified namesakes can expose a missing criterion, not supply target biography."""
    result = []
    for c in detail["candidates"]:
        a = c["assessment"]
        if a["excluded"] or c["status"] == "rejected" or a["identity_status"] == "conflicting":
            continue
        linked = a["identity_status"] == "eligible"
        result.append(
            {
                "name": c["value"]["name"],
                "review": c["status"],
                "identity_checks": a["identity_checks"],
                "facts": a["checked_facts"] if linked else [],
                "description": a["note"]
                if linked
                else "Identity unresolved; no target biography established.",
            }
        )
    return result[-12:]


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
    seeds = [*coverage_queries(brief, limit=24), *seed_queries(brief)]
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


def verification_queries(brief, candidate, page_url, checks, previous=()):
    """Test a missing relation rather than repeatedly appending all constraints."""
    name = quoted(candidate["name"])
    host = urlsplit(page_url).hostname
    groups = []
    for check in checks:
        if check["relation"] != "unknown":
            continue
        queries = []
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
            groups.append(queries)
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
        groups.append(queries)
    queries = []
    if host and not any(c["relation"] == "unknown" for c in checks):
        queries.append(
            Query(
                query=f"{name} site:{host}",
                language=brief.languages[0],
                reason="Find related public profile pages on the observed source",
            )
        )
        groups.append(queries)
    # Every missing criterion gets a turn. Remove used probes BEFORE taking the
    # bounded batch, otherwise four exhausted city probes starve school/year clues.
    seen = {normalized(q) for q in previous}
    choices = []
    for offset in range(max((len(g) for g in groups), default=0)):
        for group in groups:
            if offset < len(group):
                query = group[offset]
                key = normalized(query.query)
                if key not in seen:
                    choices.append(query)
                    seen.add(key)
    return choices[:4]
