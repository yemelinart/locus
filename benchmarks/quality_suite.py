"""Reproducible closed-corpus quality cases, runnable against an older checkout.

This is a regression benchmark, NOT open-web recall or competitor accuracy.
Search responses and semantics are scripted unless --local-model is explicit.
"""

import argparse
import asyncio
import json
import tempfile
from pathlib import Path

from locus.db import Store
from locus.engine import Engine
from locus.models import Brief, Budget, Extraction, Plan, Settings
from locus.providers.local_model import LocalModel, parse_json
from locus.providers.search import Search
from locus.verification import CandidateAudit, ObservationReview
from locus.web import Reader

NAME = "Alex Rowan"
GOOD = "Alex Rowan works as a designer in Dolynska, Ukraine."
WRONG = "Alex Rowan works as a designer in Moscow, Russia."
CITY = "Alex Rowan studied design in Dolynska."
COUNTRY = "Alex Rowan works as a designer in Ukraine."
TEXT = " This public professional profile describes design projects and educational workshops."
ROOT = "https://school.example.org/alex"
TARGET = "https://work.example.org/alex"


def long_text():
    return (
        " ".join(
            [f"Alex Rowan published design note {i}. " + "Project documentation. " * 90 for i in range(16)]
        )
        + " "
        + GOOD
        + " Appendix documentation. " * 150
    )


def cases():
    return {
        "noisy_first_index": {
            "pages": {ROOT: WRONG + TEXT, TARGET: GOOD + TEXT},
            "seeds": [],
            "target": TARGET,
            "pages_budget": 1,
            "expect": True,
        },
        "criterion_in_page_tail": {
            "pages": {ROOT: long_text()},
            "seeds": [ROOT],
            "target": ROOT,
            "expect": True,
        },
        "format_retry": {
            "pages": {ROOT: GOOD + TEXT},
            "seeds": [ROOT],
            "target": ROOT,
            "expect": True,
            "bad_once": True,
        },
        "bad_page_then_good_page": {
            "pages": {ROOT: WRONG + TEXT, TARGET: GOOD + TEXT},
            "seeds": [ROOT, TARGET],
            "target": TARGET,
            "expect": True,
            "bad_url": ROOT,
        },
        "split_profile": {
            "pages": {
                ROOT: f'<p>{CITY}{TEXT}</p><p>Alex Rowan: <a href="{TARGET}">professional portfolio</a></p>',
                TARGET: COUNTRY + TEXT,
            },
            "seeds": [ROOT],
            "target": TARGET,
            "expect": True,
            "link": True,
        },
        "wrong_city": {
            "pages": {ROOT: WRONG + TEXT},
            "seeds": [ROOT],
            "target": None,
            "expect": False,
        },
        "name_only": {
            "pages": {ROOT: "Alex Rowan published a design portfolio." + TEXT},
            "seeds": [ROOT],
            "target": None,
            "expect": False,
        },
    }


async def run_case(label, case, factory=None, settings=None):
    calls, reads, attempts = [], [], []

    class CorpusReader(Reader):
        async def _get(self, url, *args, **kwargs):
            reads.append(url)
            if url not in case["pages"]:
                raise AssertionError("Unexpected navigation outside fixture")
            return 200, "<main>" + case["pages"][url] + "</main>", "text/html", url

    class CorpusSearch(Search):
        async def _request(self, text, query, brief, backend):
            attempts.append(backend)
            if case["seeds"]:
                return []
            url = ROOT if backend == "duckduckgo" else TARGET
            return [{"url": url, "title": NAME, "snippet": case["pages"][url]}]

    class Semantics:
        def __init__(self, _):
            self.bad = False

        async def complete(self, prompt, schema):
            calls.append(schema.__name__)
            if schema is Plan:
                return Plan(queries=[])
            if schema is ObservationReview:
                return ObservationReview(grounded=True, asserts_identity=False)
            if schema is Extraction and (
                (case.get("bad_once") and not self.bad) or (case.get("bad_url") and case["bad_url"] in prompt)
            ):
                self.bad = True
                parse_json('{"candidates": [')
            quote = next(
                (q for q in [GOOD, WRONG, CITY, COUNTRY] if q in prompt),
                "Alex Rowan published a design portfolio.",
            )
            if schema is Extraction:
                return Extraction(
                    candidates=[
                        {
                            "name": NAME,
                            "facts": [{"category": "public_profile", "statement": quote, "quote": quote}],
                        }
                    ]
                )
            assert schema is CandidateAudit
            checks = []
            for field, value in [("city", "Dolynska"), ("country", "Ukraine")]:
                if value in quote:
                    checks.append(
                        {
                            "field": field,
                            "relation": "supports",
                            "quote": quote,
                            "observed": value,
                            "same_subject": True,
                            "same_place": True,
                        }
                    )
            return CandidateAudit(
                name_relation="same_spelling",
                name_quote=quote,
                claims=[{"index": 0, "verdict": "supported"}],
                identity_checks=checks,
            )

    with tempfile.TemporaryDirectory(prefix="locus-quality-") as folder:
        store = Store(Path(folder) / "fixture.sqlite")
        settings = settings or Settings(model="scripted", search_backends=["duckduckgo", "brave"])
        store.save_settings(settings)
        brief = Brief(
            name=NAME,
            city="Dolynska",
            country="Ukraine",
            languages=["en"],
            seed_urls=case["seeds"],
            budget=Budget(minutes=6, queries=1, pages=case.get("pages_budget", len(case["pages"])), rounds=1),
        )
        jid = store.create(brief)["id"]
        await Engine(store, factory or Semantics, CorpusSearch, CorpusReader).run(jid)
        before = store.detail(jid)
        if case.get("link"):
            for proposal in before.get("linkage", {}).get("proposals", []):
                # Only this fictional pair is labeled as the same person; simulate explicit review.
                store.review_link(jid, proposal["left_id"], proposal["right_id"], "confirmed")
        after = store.detail(jid)
        accepted = set(after["conclusion"]["promising_ids"])
        groups = after.get("linkage", {}).get("groups", [])
        for group in groups:
            if group["identity_status"] == "eligible":
                accepted.update(group["candidate_ids"])
        source_urls = {s["id"]: s["url"] for s in after["sources"]}
        matches = {source_urls[c["source_id"]] for c in after["candidates"] if c["id"] in accepted}
        allowed = {ROOT, TARGET} if case.get("link") else {case["target"]}
        correct = case["target"] in matches and matches <= allowed if case["expect"] else not matches
        return {
            "case": label,
            "passed": correct,
            "expected_match": case["expect"],
            "accepted_urls": sorted(matches),
            "read_urls": reads,
            "adapters": attempts,
            "status": after["status"],
            "retryable_ai": after.get("retryable_model_steps", 0),
            "model_calls": calls,
            "seconds": round(after["active_seconds"], 2),
            "matched_before_human_link": bool(
                before["conclusion"]["promising_ids"] or before["conclusion"].get("linked_matches")
            ),
        }


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--cases", nargs="*", choices=list(cases()))
    p.add_argument("--local-model", action="store_true")
    p.add_argument("--check", action="store_true", help="Fail when a labeled scenario fails")
    args = p.parse_args()
    settings, factory = None, None
    if args.local_model:
        import httpx

        async with httpx.AsyncClient(trust_env=False) as c:
            jobs = (await c.get("http://127.0.0.1:8420/api/jobs")).json()
            if any(j["status"] in {"running", "queued"} for j in jobs):
                raise SystemExit("Live research is active; local-model benchmark not started.")
            settings = Settings.model_validate((await c.get("http://127.0.0.1:8420/api/settings")).json())

        class GuardedModel(LocalModel):
            async def complete(self, prompt, schema):
                async with httpx.AsyncClient(trust_env=False) as c:
                    jobs = (await c.get("http://127.0.0.1:8420/api/jobs")).json()
                if any(j["status"] in {"running", "queued"} for j in jobs):
                    raise ValueError("User research started; benchmark yields the model.")
                import time

                began = time.monotonic()
                try:
                    return await super().complete(prompt, schema)
                finally:
                    print(
                        json.dumps({"stage": schema.__name__, "seconds": round(time.monotonic() - began, 2)}),
                        flush=True,
                    )

        factory = GuardedModel
    rows = []
    for label, case in cases().items():
        if args.cases and label not in args.cases:
            continue
        if args.local_model and label in {"format_retry", "bad_page_then_good_page"}:
            continue  # Error injection belongs to the scripted model only.
        row = await run_case(label, case, factory, settings)
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "scope": "Closed fictional corpus; not web recall. Split profile simulates explicit correct human linking.",
                "model": settings.model if settings else "scripted",
                "passed": sum(r["passed"] for r in rows),
                "total": len(rows),
                "cases": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.check and (not rows or not all(r["passed"] for r in rows)):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
