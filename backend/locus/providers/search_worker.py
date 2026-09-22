"""Short-lived non-AI search process. Never accepts executable code or cloud model credentials."""

import json
import sys

from ddgs import DDGS
from ddgs.engines import ENGINES
from ddgs.exceptions import DDGSException


def search_request(request):
    request = dict(request)
    timeout = request.pop("timeout")
    if request["backend"] not in ENGINES.get("text", {}):
        raise ValueError("Search adapter is not installed")
    DDGS.threads = 1
    try:
        hits = DDGS(timeout=timeout).text(**request)
    except DDGSException as exc:
        # Pinned ddgs 9.13: an empty aggregate/ranker result raises this exact
        # generic exception. It is not a transport error or proof of absence.
        if type(exc) is DDGSException and str(exc) == "No results found.":
            return {"results": [], "notice": "Adapter returned no results; coverage is not verified."}
        raise
    return {
        "results": [
            {"url": r["href"], "title": r.get("title", ""), "snippet": str(r.get("body", ""))[:1200]}
            for r in hits
        ]
    }


def main():
    request = json.load(sys.stdin)
    try:
        print(json.dumps(search_request(request)))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": f"Поисковый источник недоступен ({type(exc).__name__}). Попробуйте позже или подключите локальный SearXNG."
                }
            )
        )


if __name__ == "__main__":
    main()
