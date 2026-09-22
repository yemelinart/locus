"""Fixed fictional pages through the real engine. Optional local LLM; never real-person data.

This checks page reading, source trails, extraction/review, link decisions and criteria.
It is NOT a web recall benchmark: network search is deliberately stubbed.
"""

import argparse
import asyncio
import json
import tempfile
import time
from pathlib import Path

import httpx
from locus.db import Store
from locus.engine import Engine
from locus.models import Brief, Budget, Extraction, Plan, Settings
from locus.providers.local_model import LocalModel
from locus.verification import CandidateAudit, ObservationReview
from locus.web import Reader

ROOT_URL = "https://school.example.org/alex"
OTHER_URL = "https://work.example.org/alex"
PAGES = {
    ROOT_URL: """<html><title>Alex Rowan — school profile</title><main><p>Alex Rowan studied design in Dolynska.</p><p>The school publishes this professional alumni profile with permission and maintains an archive of public creative work.</p><p>Alex Rowan: <a href="https://work.example.org/alex">professional portfolio</a></p></main></html>""",
    OTHER_URL: """<html><title>Alex Rowan — portfolio</title><main><p>Alex Rowan works as a designer in Ukraine.</p><p>This public portfolio presents commissioned design projects and educational workshops. Project descriptions are published for professional reference.</p></main></html>""",
}


class CorpusReader(Reader):
    async def _get(self, url, include, exclude, check_robots=False):
        if url not in PAGES:
            raise ValueError("Outside the closed fixture corpus")
        return 200, PAGES[url], "text/html", url


class NoNetworkSearch:
    def __init__(self, _):
        self.last_audit = []

    async def search(self, query, brief):
        return []


class ScriptedModel:
    """Known semantic responses isolate engine plumbing from model accuracy."""

    def __init__(self, _):
        pass

    async def complete(self, prompt, schema):
        if schema is Plan:
            return Plan(queries=[])
        if schema is ObservationReview:
            return ObservationReview(grounded=True, asserts_identity=False)
        country = "Alex Rowan works as a designer in Ukraine." in prompt
        quote = (
            "Alex Rowan works as a designer in Ukraine."
            if country
            else "Alex Rowan studied design in Dolynska."
        )
        if schema is Extraction:
            return Extraction.model_validate(
                {
                    "candidates": [
                        {
                            "name": "Alex Rowan",
                            "facts": [{"category": "public_profile", "statement": quote, "quote": quote}],
                        }
                    ]
                }
            )
        return CandidateAudit(
            name_relation="same_spelling",
            name_quote=quote,
            claims=[{"index": 0, "verdict": "supported"}],
            identity_checks=[
                {
                    "field": "country" if country else "city",
                    "relation": "supports",
                    "quote": quote,
                    "observed": "Ukraine" if country else "Dolynska",
                    "same_subject": True,
                    "same_place": True,
                }
            ],
        )


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-model", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    settings = Settings(model="scripted-fixture")
    factory = ScriptedModel
    if args.local_model:
        async with httpx.AsyncClient(trust_env=False) as c:
            jobs = (await c.get("http://127.0.0.1:8420/api/jobs")).json()
            if any(j["status"] in {"running", "queued"} for j in jobs):
                raise SystemExit("Pause active research before a local-model benchmark.")
            settings = Settings.model_validate((await c.get("http://127.0.0.1:8420/api/settings")).json())

        class MeasuredModel(LocalModel):
            async def complete(self, prompt, schema):
                began = time.monotonic()
                result = await super().complete(prompt, schema)
                print(
                    json.dumps({"stage": schema.__name__, "seconds": round(time.monotonic() - began, 2)}),
                    flush=True,
                )
                return result

        factory = MeasuredModel
    with tempfile.TemporaryDirectory(prefix="locus-engine-replay-") as folder:
        store = Store(Path(folder) / "replay.sqlite")
        store.save_settings(settings)
        brief = Brief(
            name="Alex Rowan",
            city="Dolynska",
            country="Ukraine",
            languages=["en"],
            seed_urls=[ROOT_URL],
            budget=Budget(minutes=12, queries=1, pages=2, rounds=1),
        )
        job = store.create(brief)["id"]
        await Engine(store, factory, NoNetworkSearch, CorpusReader).run(job)
        before = store.detail(job)
        proposals = before.get("linkage", {}).get("proposals", [])
        # Simulate the explicit human decision only for the known true pair in this fictional case.
        for proposal in proposals:
            store.review_link(job, proposal["left_id"], proposal["right_id"], "confirmed")
        after = store.detail(job)
        result = {
            "model": settings.model,
            "scope": "closed fictional corpus; search stubbed; explicit correct human link simulated",
            "status": after["status"],
            "reason": after["reason"],
            "pages_read": after["stats"]["sources"],
            "candidate_cards": len(after["candidates"]),
            "proposals": len(proposals),
            "matches_before_link": before["conclusion"].get("linked_matches", 0),
            "matches_after_link": after["conclusion"].get("linked_matches", 0),
            "state": after["conclusion"]["state"],
            "seconds": round(after["active_seconds"], 2),
        }
        if args.output:
            args.output.mkdir(parents=True, exist_ok=True)
            (args.output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
            (args.output / "research.json").write_text(json.dumps(after, ensure_ascii=False, indent=2))
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if after.get("linkage") is not None and not (
            result["pages_read"] == 2
            and result["matches_before_link"] == 0
            and result["matches_after_link"] == 1
        ):
            raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
