"""Opt-in live discovery for known public computer scientists, with no seed URLs.

Small diagnostic, NOT a representative people-finding or competitor benchmark.
Uses the real engine, readers, selected search adapters and local model in an
isolated database. Requires installed Locus, with user research paused.
"""

import argparse
import asyncio
import json
import tempfile
from pathlib import Path

import httpx
from locus.db import Store
from locus.engine import Engine
from locus.models import Brief, Budget, Settings

TARGETS = {
    "guido": {"name": "Guido van Rossum", "city": "Haarlem", "country": "Netherlands"},
    "knuth": {"name": "Donald Knuth", "city": "Milwaukee", "country": "United States"},
}


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=TARGETS, default="guido")
    parser.add_argument("--minutes", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path(".qa/v061/discovery"))
    args = parser.parse_args()
    async with httpx.AsyncClient(trust_env=False, timeout=15) as client:
        jobs = (await client.get("http://127.0.0.1:8420/api/jobs")).json()
        if any(j["status"] in {"running", "queued"} for j in jobs):
            raise SystemExit("Pause research before testing.")
        settings = Settings.model_validate((await client.get("http://127.0.0.1:8420/api/settings")).json())
    with tempfile.TemporaryDirectory(prefix="locus-discovery-") as temp:
        store = Store(Path(temp) / "test.sqlite")
        store.save_settings(settings)
        brief = Brief(
            **TARGETS[args.case],
            languages=["en"],
            budget=Budget(minutes=args.minutes, queries=5, pages=6, rounds=2),
        )
        job = store.create(brief)["id"]
        task = asyncio.create_task(Engine(store).run(job))
        previous = ""
        while not task.done():
            await asyncio.wait({task}, timeout=10)
            phase = json.dumps(store.job(job)["activity"], ensure_ascii=False)
            if phase != previous:
                print(phase, flush=True)
                previous = phase
        await task
        detail = store.detail(job)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "research.json").write_text(json.dumps(detail, ensure_ascii=False, indent=2))
        result = {
            "scope": "one known public target; no seed URLs or domain restrictions; not general accuracy",
            "brief": brief.model_dump(),
            "model": settings.model,
            "seconds": round(detail["active_seconds"], 2),
            "status": detail["status"],
            "reason": detail["reason"],
            "stats": detail["stats"],
            "conclusion": detail["conclusion"],
            "sources": [
                {"url": s["url"], "status": s["status"], "error": s["error"]} for s in detail["sources"]
            ],
            "search_runs": detail["search_runs"],
        }
        (args.output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
