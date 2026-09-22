"""Opt-in bounded real-web smoke: public Python creator biography, local AI only.

This is one known public target with a supplied starting URL, not a blind discovery benchmark.
Never touches the installed research database or changes settings.
"""

import asyncio
import json
import tempfile
from pathlib import Path

import httpx
from locus.db import Store
from locus.engine import Engine
from locus.models import Brief, Budget, EvidenceClue, Settings


async def main():
    async with httpx.AsyncClient(trust_env=False) as client:
        jobs = (await client.get("http://127.0.0.1:8420/api/jobs")).json()
        if any(j["status"] in {"running", "queued"} for j in jobs):
            raise SystemExit("Pause research before testing.")
        settings = Settings.model_validate((await client.get("http://127.0.0.1:8420/api/settings")).json())
    with tempfile.TemporaryDirectory(prefix="locus-public-smoke-") as temp:
        store = Store(Path(temp) / "smoke.sqlite")
        store.save_settings(settings)
        brief = Brief(
            name="Guido van Rossum",
            languages=["en"],
            seed_urls=["https://gvanrossum.github.io/bio.html"],
            include_domains=["gvanrossum.github.io", "python.org"],
            evidence_clues=[EvidenceClue(kind="public_work", text="Python")],
            budget=Budget(minutes=6, queries=1, pages=2, rounds=1),
        )
        job = store.create(brief)["id"]
        task = asyncio.create_task(Engine(store).run(job))
        previous = ""
        while not task.done():
            await asyncio.wait({task}, timeout=10)
            snapshot = store.job(job)
            phase = json.dumps(snapshot["activity"], ensure_ascii=False)
            if phase != previous:
                print(phase, flush=True)
                previous = phase
        await task
        detail = store.detail(job)
        output = Path(".qa/v06/public-smoke")
        output.mkdir(parents=True, exist_ok=True)
        (output / "research.json").write_text(json.dumps(detail, ensure_ascii=False, indent=2))
        result = {
            "scope": "one public professional target, seeded URL; not a recall benchmark",
            "model": settings.model,
            "status": detail["status"],
            "reason": detail["reason"],
            "stats": detail["stats"],
            "conclusion": detail["conclusion"],
            "seconds": round(detail["active_seconds"], 2),
            "sources": [
                {"url": s["url"], "status": s["status"], "error": s["error"]} for s in detail["sources"]
            ],
        }
        (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
