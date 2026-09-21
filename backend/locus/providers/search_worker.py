"""Short-lived non-AI search process. Never accepts executable code or cloud model credentials."""

import json
import sys

from ddgs import DDGS
from ddgs.engines import ENGINES


def main():
    request = json.load(sys.stdin)
    timeout = request.pop("timeout")
    try:
        if request["backend"] not in ENGINES.get("text", {}):
            raise ValueError("Search adapter is not installed")
        DDGS.threads = 1
        hits = DDGS(timeout=timeout).text(**request)
        print(json.dumps({"results": [{"url": r["href"], "title": r.get("title", "")} for r in hits]}))
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
