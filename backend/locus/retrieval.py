"""Rank discovery evidence, never use search snippets to establish identity."""

import re
from functools import lru_cache

from .names import name_in, variants
from .places import country_codes, forms, gazetteer, search_spellings
from .web import canonical_url, domain_allowed


@lru_cache(maxsize=256)
def country_spellings(country):
    codes = country_codes(country) if country else set()
    return tuple(
        dict.fromkeys(
            [country, *[a for code in sorted(codes) for a in gazetteer()[0]["countries"][code] if len(a) > 2]]
        )
    )


def anchors(brief, body=None):
    groups = []
    if brief.city.strip():
        groups.append(("city", search_spellings(brief.city, brief.country)))
    if brief.country.strip():
        groups.append(("country", country_spellings(brief.country)))
    if brief.year_from or brief.year_to:
        # Discovery prefers the requested range. Reading must also retain a
        # different stated year so the reviewer can detect contradictions.
        years = (
            re.findall(r"\b(?:18|19|20)\d{2}\b", body)
            if body is not None
            else [str(y) for y in range(brief.year_from or 1850, (brief.year_to or 2100) + 1)]
        )
        groups.append(("birth_year", years))
    groups.extend((f"clue:{i}", [c.text]) for i, c in enumerate(brief.evidence_clues))
    return groups


def phrase_in(text, phrase):
    return any(re.search(r"(?<!\w)" + re.escape(f) + r"(?!\w)", text) for f in forms(phrase) if f)


def signals(result, brief):
    from .places import key

    raw = result.get("title", "") + " " + result.get("snippet", "")
    text = key(raw)
    return {
        "name": name_in(raw, [v["name"] for v in variants(brief)]),
        "anchors": [field for field, values in anchors(brief) if any(phrase_in(text, v) for v in values)],
    }


def score(result, brief):
    s = signals(result, brief)
    # An anchored namesake deserves reading priority, not match acceptance.
    return (3 if s["name"] else 0) + sum(
        5 if f == "city" else 2 if f == "country" else 4 for f in s["anchors"]
    )


def contextual_results(results, brief):
    requested = {field for field, _ in anchors(brief)}
    # Country alone must not end index exploration when the user gave a city.
    # These are only triage signals; their presence still proves no relation.
    return any((s := signals(r, brief))["name"] and requested.issubset(s["anchors"]) for r in results)


def merge_results(results, brief, limit):
    unique = {}
    for row in results:
        try:
            url = canonical_url(row["url"])
        except (ValueError, KeyError, TypeError):
            continue
        if not domain_allowed(url, brief.include_domains, brief.exclude_domains):
            continue
        item = dict(row, url=url)
        if url not in unique or score(item, brief) > score(unique[url], brief):
            unique[url] = item
    return sorted(unique.values(), key=lambda r: score(r, brief), reverse=True)[:limit]
