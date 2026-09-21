import asyncio
import json
import sys
import time

import httpx
from ddgs.engines import ENGINES

from ..db import now
from ..models import Brief, Query, Settings

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
            # Rotate over enabled adapters; at most one fallback. Every attempt is recorded.
            offset = self.cursor % len(engines)
            self.cursor += 1
            engines = (engines[offset:] + engines[:offset])[:2]
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
                    return results
            except asyncio.CancelledError:
                audit["status"] = "cancelled"
                raise
            except Exception as exc:
                audit["error"] = str(exc)[:400]
            finally:
                audit["seconds"] = round(time.monotonic() - began, 3)
                self.last_audit.append(audit)
        if all(a["status"] == "failed" for a in self.last_audit):
            raise ValueError(
                "Selected search engines did not respond. Check their availability or try again later."
            )
        return []

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
            return [{"url": r["url"], "title": r.get("title", "")} for r in results]
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
            "region": REGIONS.get(query.language, "wt-wt")
            if self.settings.search_region == "auto"
            else self.settings.search_region,
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
