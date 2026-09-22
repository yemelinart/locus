"""Bounded literal quotation choices. Co-occurrence is never identity evidence."""

import re

from .names import name_pattern
from .places import forms
from .retrieval import anchors


def evidence_passages(excerpt, brief, candidate_name):
    names = list(re.finditer(name_pattern(candidate_name), excerpt, re.I))[:64]
    groups = anchors(brief, excerpt)
    result, seen = [], set()
    for field, values in groups:
        choices = []
        terms = sorted({v for term in values for v in forms(term) if len(v) >= 3})
        for term in terms:
            for anchor in list(re.finditer(r"(?<!\w)" + re.escape(term) + r"(?!\w)", excerpt, re.I))[:32]:
                for name in names:
                    first, last = min(anchor.start(), name.start()), max(anchor.end(), name.end())
                    if last - first > 330:
                        continue
                    a, b = max(0, first - 35), min(len(excerpt), last + 110)
                    quote = excerpt[a:b]
                    if "[... omitted source text ...]" in quote:
                        continue
                    choices.append((last - first, a, quote))
        added = 0
        for _, _, quote in sorted(choices):
            if quote in seen:
                continue
            seen.add(quote)
            result.append({"id": len(result), "field": field, "text": quote})
            added += 1
            if added == 2 or len(result) == 12:
                break
        if len(result) == 12:
            break
    return result


def resolve_passage(check, passages):
    if check.passage_id is None:
        return check
    if check.passage_id >= len(passages):
        return check.model_copy(update={"quote": "", "same_subject": False})
    text = passages[check.passage_id]["text"]
    if check.quote and " ".join(check.quote.split()) != " ".join(text.split()):
        return check.model_copy(update={"quote": "", "same_subject": False})
    return check.model_copy(update={"quote": text})
