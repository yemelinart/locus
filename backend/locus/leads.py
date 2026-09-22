"""Visible retrieval leads, kept strictly outside verified person findings."""

from urllib.parse import unquote, urlsplit

from .models import Brief
from .names import name_in, variants
from .retrieval import score
from .web import canonical_url, domain_allowed


def build_leads(detail, tasks):
    brief = Brief.model_validate(detail["brief"])
    names = [x["name"] for x in variants(brief)]
    sources = {u: s for s in detail["sources"] for u in [s["url"], *s.get("url_aliases", [])]}
    result = {}
    for task in tasks:
        p = task["payload"]
        try:
            url = canonical_url(p["url"])
        except (KeyError, ValueError):
            continue
        if not domain_allowed(url, brief.include_domains, brief.exclude_domains):
            continue
        # A city directory without the person's name is not a person lead.
        title, snippet = p.get("title", ""), p.get("snippet", "")
        if not name_in(title + " " + snippet, names):
            continue
        source = sources.get(url)
        state = (
            source["status"]
            if source
            else "queued"
            if task["state"] in {"pending", "running"}
            else "deferred"
        )
        host = urlsplit(url).hostname or ""
        profile = any(
            host == d or host.endswith("." + d)
            for d in ("linkedin.com", "facebook.com", "vk.com", "orcid.org", "researchgate.net")
        )
        result[url] = {
            "id": task["id"],
            "url": url,
            "title": title or unquote(url),
            "snippet": snippet,
            "query": p.get("query", ""),
            "state": state,
            "source_id": source["id"] if source else None,
            "error": source.get("error", "") if source else "",
            "rank": score(p, brief) + 5 * profile,
        }
    return sorted(result.values(), key=lambda r: -r["rank"])
