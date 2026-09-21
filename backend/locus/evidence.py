"""Explainable evidence support, never a calibrated identity probability."""

import re
import unicodedata

from .web import domain_allowed

LABELS = {
    "insufficient": ("Insufficient evidence", "Недостаточно свидетельств"),
    "limited": ("Limited support", "Слабая обоснованность"),
    "supported": ("Supporting clues", "Есть подтверждающие ориентиры"),
    "strong": ("Multiple supporting clues", "Несколько подтверждающих ориентиров"),
    "conflicting": ("Needs conflict review", "Нужно проверить противоречия"),
    "excluded": ("Archived by current filters", "В архиве по текущим фильтрам"),
}


def contains(text, phrase):
    def norm(value):
        return " ".join(unicodedata.normalize("NFKC", value).casefold().split())

    return bool(re.search(r"(?<!\w)" + re.escape(norm(phrase)) + r"(?!\w)", norm(text)))


def assess(candidate, source, brief, revision):
    value = candidate["value"]
    facts = value.get("facts", [])
    quotes = [f["quote"] for f in facts]
    names = [brief["name"], *brief.get("aliases", []), *brief.get("previous_names", [])]
    name_quote = next((q for q in quotes if any(contains(q, name) for name in names)), "")
    supported, missing = [], []
    categories = {
        "education": {"education"},
        "organization": {"organization", "professional_role"},
        "public_work": {"publication", "public_work"},
    }
    for clue in brief.get("evidence_clues", []):
        quote = next(
            (
                f["quote"]
                for f in facts
                if f["category"] in categories[clue["kind"]] and contains(f["quote"], clue["text"])
            ),
            "",
        )
        if quote:
            supported.append(clue | {"quote": quote})
        else:
            missing.append(clue)
    kinds = {c["kind"] for c in supported}
    level = "insufficient"
    if name_quote:
        level = "strong" if len(kinds) >= 2 else "supported" if kinds else "limited"
    flags = value.get("contradictions", [])
    if flags:
        level = "conflicting"
    excluded = bool(source.get("url")) and not domain_allowed(
        source["url"], brief.get("include_domains", []), brief.get("exclude_domains", [])
    )
    if excluded:
        level = "excluded"
    return {
        "level": level,
        "name_quote": name_quote,
        "supported": supported,
        "missing": missing,
        "flags": flags,
        "excluded": excluded,
        "revision": revision,
        "review_outdated": candidate["status"] != "unreviewed"
        and candidate.get("review_revision", 1) < revision,
        "method": "quote-clues-v1",
    }
