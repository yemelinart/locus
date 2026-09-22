import asyncio
import json
import sys
import time
from datetime import datetime, timezone

import httpx
from ddgs.engines import ENGINES

from ..db import now
from ..models import Brief, Query, Settings
from ..retrieval import contextual_results, merge_results

REGIONS = {
    "ru": "ru-ru",
    "en": "us-en",
    "uk": "ua-uk",
    "de": "de-de",
    "fr": "fr-fr",
    "es": "es-es",
    "it": "it-it",
    "pt": "pt-pt",
    "tr": "tr-tr",
    "pl": "pl-pl",
    "zh": "cn-zh",
    "ja": "jp-jp",
}
LABELS = {
    "duckduckgo": "DuckDuckGo",
    "bing": "Bing",
    "brave": "Brave",
    "mojeek": "Mojeek",
    "yahoo": "Yahoo",
    "google": "Google",
    "yandex": "Yandex",
    "wikipedia": "Wikipedia",
    "startpage": "Startpage",
}


def target_region(settings, brief, language, scope="auto"):
    if settings.search_region != "auto":
        return settings.search_region
    if scope == "worldwide":
        return "wt-wt"
    country = brief.country.strip().casefold()
    if country in {"ukraine", "украина", "україна"}:
        return REGIONS["uk"]
    # An English query about a supplied country must not silently prefer the US.
    return "wt-wt" if country else REGIONS.get(language, "wt-wt")


def catalog():
    installed = ENGINES.get("text", {})
    return [
        {
            "id": key,
            "name": label,
            "available": key in installed,
            "kind": "reference" if key == "wikipedia" else "web",
        }
        for key, label in LABELS.items()
    ]


class Search:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.last_audit = []
        self.cursor = 0
        self.health = {}

    def restore_health(self, attempts):
        for a in sorted(attempts, key=lambda a: a["at"]):
            try:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(a["at"])).total_seconds()
            except (ValueError, TypeError):
                continue
            if age < 120:
                self._health_result(a["engine"], a["status"], cooldown=max(0, 120 - age))

    def _health_result(self, engine, status, cooldown=120):
        health = self.health.setdefault(engine, {"failures": 0, "until": 0})
        if status in {"ok", "empty"}:
            health.update(failures=0, until=0)
        elif status == "failed":
            health["failures"] += 1
            if health["failures"] >= 2:
                health["until"] = time.monotonic() + cooldown

    async def search(self, query: Query, brief: Brief) -> list[dict]:
        text = query.query
        if brief.include_domains:
            text += " (" + " OR ".join("site:" + d for d in brief.include_domains) + ")"
        text += "".join(" -site:" + d for d in brief.exclude_domains)
        self.last_audit = []
        if self.settings.search_provider == "searxng":
            engines = ["searxng"]
        else:
            engines = [
                e for e in dict.fromkeys(self.settings.search_backends) if e in ENGINES.get("text", {})
            ]
            if not engines:
                raise ValueError("No selected search adapter is installed. Check search settings.")
            # Rotate over enabled adapters; up to two fallbacks, skipping temporary outages. Every attempt is recorded.
            offset = self.cursor % len(engines)
            self.cursor += 1
            rotated = engines[offset:] + engines[:offset]
            ready = [e for e in rotated if self.health.get(e, {}).get("until", 0) <= time.monotonic()]
            if not ready:
                raise ValueError(
                    "All selected search engines are temporarily unavailable. Results are incomplete; retry later."
                )
            engines = ready[:3]
        gathered = []
        nonempty = 0
        for backend in engines:
            began = time.monotonic()
            audit = {
                "engine": backend,
                "at": now(),
                "status": "failed",
                "result_count": 0,
                "seconds": 0,
                "error": "",
            }
            try:
                results = await self._request(text, query, brief, backend)
                audit.update(status="ok" if results else "empty", result_count=len(results))
                if results:
                    gathered.extend(results)
                    nonempty += 1
                    # Nonempty does not mean relevant: a second selected index may
                    # surface the missing connection. Keep weak leads, dedup and rank.
                    usable = merge_results(gathered, brief, self.settings.results_per_query)
                    if contextual_results(usable, brief) or nonempty >= 2:
                        return usable
            except asyncio.CancelledError:
                audit["status"] = "cancelled"
                raise
            except Exception as exc:
                audit["error"] = str(exc)[:400]
            finally:
                audit["seconds"] = round(time.monotonic() - began, 3)
                self.last_audit.append(audit)
                self._health_result(backend, audit["status"])
        if all(a["status"] == "failed" for a in self.last_audit):
            raise ValueError(
                "Selected search engines did not respond. Check their availability or try again later."
            )
        return merge_results(gathered, brief, self.settings.results_per_query)

    async def _request(self, text, query, brief, backend):
        if backend == "searxng":
            params = {
                "q": text,
                "format": "json",
                "language": query.language,
                "categories": "general",
                "safesearch": {"off": 0, "moderate": 1, "on": 2}[self.settings.safesearch],
            }
            if brief.freshness != "all":
                params["time_range"] = {"d": "day", "w": "week", "m": "month", "y": "year"}[brief.freshness]
            async with httpx.AsyncClient(
                timeout=self.settings.request_timeout, trust_env=False, follow_redirects=False
            ) as client:
                response = await client.get(self.settings.searxng_url + "/search", params=params)
                response.raise_for_status()
                data = response.json()
            results = data.get("results", [])[: self.settings.results_per_query]
            if not results and data.get("unresponsive_engines"):
                raise ValueError("SearXNG engines are unavailable; this does not mean no matches exist.")
            return [
                {"url": r["url"], "title": r.get("title", ""), "snippet": str(r.get("content", ""))[:1200]}
                for r in results
            ]
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "locus.providers.search_worker",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        payload = {
            "query": text,
            "region": target_region(self.settings, brief, query.language, query.scope),
            "max_results": self.settings.results_per_query,
            "backend": backend,
            "timeout": self.settings.request_timeout,
            "safesearch": self.settings.safesearch,
            "timelimit": None if brief.freshness == "all" else brief.freshness,
        }
        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(json.dumps(payload).encode()), self.settings.request_timeout + 10
            )
            result = json.loads(stdout)
            if "error" in result:
                raise ValueError(result["error"])
            return result["results"]
        finally:
            if process.returncode is None:
                process.kill()
            await process.wait()
