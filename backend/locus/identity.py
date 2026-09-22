"""Required identity criteria, with explicit unknowns and source-grounded comparisons."""

import re
import unicodedata
from typing import Literal

from pydantic import Field

from .models import Model


def normalized(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def required(brief, include_clues=False):
    b = brief.model_dump() if hasattr(brief, "model_dump") else brief
    result = [{"field": k, "requested": b[k].strip()} for k in ("city", "country") if b.get(k, "").strip()]
    if b.get("year_from") or b.get("year_to"):
        result.append(
            {"field": "birth_year", "requested": f"{b.get('year_from') or '…'}–{b.get('year_to') or '…'}"}
        )
    if include_clues:
        result.extend(
            {"field": f"clue:{i}", "requested": c["text"]} for i, c in enumerate(b.get("evidence_clues", []))
        )
    return result


def with_clues(checks, brief, supported, conflicts):
    rows = list(checks)
    for i, clue in enumerate(brief.evidence_clues):
        positive = next((c for c in supported if c["index"] == i), None)
        negative = next((c for c in conflicts if c["index"] == i), None)
        evidence = negative or positive
        rows.append(
            {
                "field": f"clue:{i}",
                "requested": clue.text,
                "relation": "contradicts" if negative else "supports" if positive else "unknown",
                "quote": evidence["quote"] if evidence else "",
                "observed": clue.text if evidence else "",
            }
        )
    return rows


class IdentityCheck(Model):
    field: Literal["city", "country", "birth_year"]
    relation: Literal["supports", "contradicts", "unknown"] = "unknown"
    quote: str = Field(default="", max_length=500)
    observed: str = Field(default="", max_length=160)
    same_subject: bool = False
    same_place: bool = False
    birth_year: int | None = Field(default=None, ge=1850, le=2100)


def validate_checks(checks, brief, candidate_name, body, excerpt):
    result = []
    for criterion in required(brief):
        field = criterion["field"]
        matches = [c for c in checks if c.field == field]
        row = criterion | {"relation": "unknown", "quote": "", "observed": ""}
        if len(matches) == 1:
            c = matches[0]
            q = " ".join(c.quote.split())
            grounded = (
                len(q) >= 12
                and q in " ".join(body.split())
                and q in " ".join(excerpt.split())
                and c.same_subject
                and re.search(r"(?<!\w)" + re.escape(normalized(candidate_name)) + r"(?!\w)", normalized(q))
                and c.observed.strip()
                and normalized(c.observed) in normalized(q)
            )
            if grounded:
                relation = c.relation
                if field == "birth_year":
                    # The model identifies the birth-year relation; arithmetic is never delegated.
                    year = c.birth_year
                    birth_context = re.search(
                        r"born|birth|родил|родив|народ|gebor|né\b|née\b|nac[ií]|nasc|doğ|urodz|出生|生まれ",
                        q,
                        re.I,
                    )
                    negated_birth = re.search(
                        r"not born|wasn't born|не родил|не родив|не народ|nicht geboren", q, re.I
                    )
                    if (
                        year is None
                        or not re.search(rf"(?<!\d){year}(?!\d)", q)
                        or not birth_context
                        or negated_birth
                    ):
                        relation = "unknown"
                    elif relation != "unknown":
                        inside = (brief.year_from is None or year >= brief.year_from) and (
                            brief.year_to is None or year <= brief.year_to
                        )
                        relation = "supports" if inside else "contradicts"
                elif relation == "supports" and not c.same_place:
                    relation = "unknown"
                elif relation == "contradicts":
                    # A different place is not a disproof of past connections, even if the LLM says so.
                    denial = re.search(
                        r"no (?:biographical )?(?:connection|ties|association)|никак\w* связ|не (?:имеет|має).*связ|жодн\w* зв['’]яз",
                        q,
                        re.I,
                    )
                    if not denial or normalized(criterion["requested"]) not in normalized(q):
                        relation = "unknown"
                row.update(relation=relation, quote=c.quote, observed=c.observed)
        result.append(row)
    return result


def resolution(checks, has_name):
    if not checks:
        return "no_constraints"
    if any(c["relation"] == "contradicts" for c in checks):
        return "conflicting"
    if has_name and all(c["relation"] == "supports" for c in checks):
        return "eligible"
    return "unresolved"


def discovery_priority(result, brief):
    """Triage only: snippets affect reading order, never candidate identity evidence."""
    text = normalized(result.get("title", "") + " " + result.get("snippet", ""))
    score = 0
    for value, weight in [(brief.name, 3), (brief.city, 5), (brief.country, 2)]:
        if value.strip() and normalized(value) in text:
            score += weight
    return score


IDENTITY_INSTRUCTIONS = (
    "For EACH required identity criterion return identity_checks with field, relation, quote, observed, "
    "same_subject, same_place and birth_year when applicable. Missing evidence is UNKNOWN, never support. "
    "City means a biographical connection to the specified city (origin, former residence, education or work), "
    "not necessarily current residence. Respect every supplied region/country qualifier; Alexandria in Egypt "
    "is not Oleksandriia in Kirovohrad. Recognize genuine translations/transliterations of the SAME place, "
    "not similarly named places. Country requires an explicitly attributed connection, not the website language or domain. "
    "A page footer, another person's location, publication venue, or mere mention of a city is NOT evidence about this person. "
    "same_subject=true ONLY when the quote explicitly attributes the observation to this candidate. "
    "The exact quote must contain the candidate's full name and the observed value. If not available, leave unknown. "
    "same_place=true only for the requested place or its unambiguous equivalent. Different current residence, nationality "
    "or workplace alone does not disprove an earlier connection: leave unknown. Contradicts requires explicit incompatible "
    "evidence about the SAME relation/time, such as an explicit denial of the requested connection. "
    "For birth_year use only a publicly stated YEAR OF BIRTH, not publication, graduation, employment or death year. "
    "Never estimate birth year from appearance or graduation dates. Do not seek private contacts or exact birth dates. "
)
