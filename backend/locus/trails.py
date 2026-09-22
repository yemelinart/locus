"""Observed public hyperlinks: bounded navigation leads, never identity proof."""

import json
import re
from urllib.parse import urljoin, urlsplit

from .web import canonical_url, domain_allowed


def extract_links(soup, base_url):
    links, seen = [], set()

    def add(href, context, kind, person=""):
        if not isinstance(href, str):
            return
        try:
            url = canonical_url(urljoin(base_url, href))
        except ValueError:
            return
        key = (url, person, context[:600])
        if url == canonical_url(base_url) or key in seen or len(links) >= 100:
            return
        seen.add(key)
        links.append({"url": url, "context": context[:600], "kind": kind, "person": person[:160]})

    def structured(value, depth=0):
        if depth > 6:
            return
        if isinstance(value, list):
            for item in value[:100]:
                structured(item, depth + 1)
        elif isinstance(value, dict):
            types = value.get("@type", [])
            if types == "Person" or isinstance(types, list) and "Person" in types:
                name = value.get("name", "")
                if isinstance(name, str) and name:
                    same = value.get("sameAs", [])
                    for href in ([same] if isinstance(same, str) else same if isinstance(same, list) else [])[
                        :12
                    ]:
                        add(href, name, "declared_same_as", name)
            for key in ("@graph", "mainEntity", "author", "about"):
                structured(value.get(key), depth + 1)

    for script in soup.find_all("script", type="application/ld+json")[:20]:
        try:
            structured(json.loads(script.get_text()))
        except (ValueError, TypeError, RecursionError):
            pass
    heading_tag = soup.find("h1")
    heading = heading_tag.get_text(" ", strip=True)[:200] if heading_tag else ""
    for anchor in soup.find_all("a", href=True)[:600]:
        if anchor.find_parent(["nav", "footer", "header", "form"]):
            continue
        parent = anchor.find_parent(["p", "li", "figcaption", "td"])
        anchor_text = anchor.get_text(" ", strip=True)
        context = (parent or anchor).get_text(" ", strip=True)
        # Malformed unclosed paragraphs can include the entire page; keep the window around this link.
        if len(context) > 600 and anchor_text:
            position = context.find(anchor_text)
            context = context[max(0, position - 200) : max(0, position - 200) + 600]
        add(anchor["href"], context, "hyperlink")
        same_host = urlsplit(urljoin(base_url, anchor["href"])).hostname == urlsplit(base_url).hostname
        if (
            heading
            and same_host
            and re.fullmatch(
                r"(?i)(?:(?:my|brief|professional|public)\s+)?(?:bio(?:graphy)?|resume|résumé|cv|portfolio|publications?|about(?: me)?|биография|резюме|портфолио|публикации|про мене|о себе)",
                anchor_text,
            )
        ):
            add(anchor["href"], heading + " → " + anchor_text, "profile_navigation", heading)
    return links


def relevant_links(links, names, include=(), exclude=()):
    from .verification import contains_name

    return [
        link
        for link in links
        if contains_name(link.get("person") or link.get("context", ""), names)
        and domain_allowed(link["url"], list(include), list(exclude))
    ][:6]
