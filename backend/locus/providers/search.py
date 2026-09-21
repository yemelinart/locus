import asyncio
import json
import sys

import httpx

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


class Search:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def search(self, query: Query, brief: Brief) -> list[dict]:
        text = query.query
        if brief.include_domains:
            text += " (" + " OR ".join("site:" + d for d in brief.include_domains) + ")"
        text += "".join(" -site:" + d for d in brief.exclude_domains)
        if self.settings.search_provider == "searxng":
            params = {"q": text, "format": "json", "language": query.language, "categories": "general"}
            if brief.freshness != "all":
                params["time_range"] = {"d": "day", "w": "week", "m": "month", "y": "year"}[brief.freshness]
            async with httpx.AsyncClient(timeout=self.settings.request_timeout, trust_env=False) as client:
                response = await client.get(self.settings.searxng_url + "/search", params=params)
                response.raise_for_status()
                data = response.json()
            results = data.get("results", [])[: self.settings.results_per_query]
            if not results and data.get("unresponsive_engines"):
                raise ValueError(
                    "Поисковые системы SearXNG недоступны; это не означает отсутствие результатов"
                )
            return [{"url": r["url"], "title": r.get("title", "")} for r in results]
        # Isolate the synchronous search client so pause/timeout really terminates the request.
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
            "region": REGIONS.get(query.language, "wt-wt"),
            "max_results": self.settings.results_per_query,
            "backend": ",".join(self.settings.search_backends),
            "timeout": self.settings.request_timeout,
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
