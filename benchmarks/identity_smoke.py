"""Local-model identity-filter checks on fictional public-profile snippets, not real people.

Run with the Locus server available and all research paused. No settings are changed.
"""

import argparse
import asyncio
import json
import time

import httpx
from locus.identity import resolution
from locus.models import Brief, Settings
from locus.providers.local_model import LocalModel
from locus.verification import CandidateAudit, audit_prompt, validate_audit

CASES = [
    ("same_place_and_year", "Alex Rowan is a designer from Dolynska, Ukraine, born in 1982.", "eligible"),
    ("namesake_other_country", "Alex Rowan is a designer from Oryol, Russia, born in 1982.", "unresolved"),
    (
        "footer_is_not_person_location",
        "Alex Rowan is a designer, born in 1982. Website publisher office: Dolynska, Ukraine.",
        "unresolved",
    ),
    (
        "other_person_location",
        "Alex Rowan is a designer, born in 1982. Maya Chen grew up in Dolynska, Ukraine.",
        "unresolved",
    ),
    (
        "past_connection_despite_move",
        "Alex Rowan is a designer, born in 1982, who grew up in Dolynska, Ukraine and later moved to Berlin, Germany.",
        "eligible",
    ),
    ("birth_outside_range", "Alex Rowan is a designer from Dolynska, Ukraine, born in 1995.", "conflicting"),
    (
        "publication_year_not_birth",
        "Alex Rowan is a designer from Dolynska, Ukraine who published a book in 1982.",
        "unresolved",
    ),
    (
        "missing_all_constraints",
        "Alex Rowan is a designer. No further biographical details are provided.",
        "unresolved",
    ),
    (
        "ukrainian_place_spelling",
        "Alex Rowan — дизайнер з міста Долинська, Україна, народився 1982 року.",
        "eligible",
    ),
    (
        "same_city_name_wrong_country",
        "Alex Rowan is a designer from Alexandria, Egypt, born in 1982.",
        "unresolved",
    ),
]


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="Comma-separated case names")
    args = parser.parse_args()
    async with httpx.AsyncClient(trust_env=False, timeout=15) as c:
        jobs = (await c.get("http://127.0.0.1:8420/api/jobs")).json()
        if any(j["status"] in {"running", "queued"} for j in jobs):
            raise SystemExit("Pause research before testing.")
        settings = Settings.model_validate((await c.get("http://127.0.0.1:8420/api/settings")).json())
    model = LocalModel(settings)
    brief = Brief(
        name="Alex Rowan", city="Dolynska", country="Ukraine", year_from=1980, year_to=1984, languages=["en"]
    )
    rows = []
    for name, body, expected in CASES:
        if args.only and name not in args.only.split(","):
            continue
        case_brief = brief.model_copy(deep=True)
        if name == "ukrainian_place_spelling":
            case_brief.city = "Долинская"
            case_brief.country = "Украина"
        if name == "same_city_name_wrong_country":
            case_brief.city = "Alexandria, Kirovohrad region"
        start = time.monotonic()
        value = {
            "name": brief.name,
            "facts": [{"category": "professional_role", "statement": "Designer", "quote": body}],
        }
        try:
            raw = await asyncio.wait_for(
                model.complete(audit_prompt(value, case_brief, body), CandidateAudit), 150
            )
            audit = validate_audit(raw, value, case_brief, body, body)
            actual = resolution(audit["identity_checks"], bool(audit["name_quote"]))
            row = {
                "case": name,
                "expected": expected,
                "actual": actual,
                "passed": actual == expected,
                "checks": audit["identity_checks"],
            }
        except Exception as e:
            row = {"case": name, "passed": False, "error": str(e)[:200]}
        row.update(seconds=round(time.monotonic() - start, 2), model=settings.model)
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    print(
        json.dumps(
            {
                "passed": sum(r["passed"] for r in rows),
                "total": len(rows),
                "scope": "synthetic snippets, not a recall or accuracy benchmark",
            }
        ),
        flush=True,
    )
    if not rows or not all(r["passed"] for r in rows):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
