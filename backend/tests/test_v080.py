import json

from locus.db import Store
from locus.discovery import coverage_queries, planning_findings, portfolio
from locus.engine import Engine
from locus.models import Brief, Budget, Settings
from locus.providers.search import target_region
from locus.reports import markdown


def test_common_latin_spelling_is_searched_without_city_or_country():
    brief = Brief(name="Юлия Тестенко", city="Долинька", country="Украина", languages=["en", "uk"])
    probes = coverage_queries(brief)
    assert len(probes) <= 4
    assert probes[1].query == '"Yulia Testenko"'
    assert "Testenko Yulia" in [q.query for q in probes]
    assert all(brief.city not in q.query and q.scope == "worldwide" for q in probes)
    assert target_region(Settings(), brief, "en", probes[1].scope) == "wt-wt"
    assert target_region(Settings(search_region="ca-en"), brief, "en", "worldwide") == "ca-en"
    restricted = Brief(name=brief.name, expand_names=False)
    assert all("Yulia" not in q.query for q in coverage_queries(restricted))


def test_later_rounds_reach_unused_spellings_without_repeating_first_batch():
    brief = Brief(name="Сергей Тестов", city="Example City")
    seen = [q.query for q in coverage_queries(brief)]
    wanted = '"Sergey Tiestov"'
    for _ in range(10):
        rows = portfolio(brief, [], seen, 12)
        assert not set(seen).intersection(q.query for q in rows)
        seen.extend(q.query for q in rows)
    assert wanted in seen


def test_unknown_namesake_biography_cannot_contaminate_global_plan():
    a = dict(
        excluded=False,
        identity_status="unresolved",
        identity_checks=[],
        checked_facts=[{"statement": "Wrote an unrelated book"}],
        note="Unrelated author",
    )
    candidate = {"value": {"name": "Alex Rowan"}, "status": "unreviewed", "assessment": a}
    rows = planning_findings({"candidates": [candidate]})
    assert rows[0]["facts"] == [] and "Unrelated author" not in json.dumps(rows)
    a["identity_status"] = "eligible"
    assert planning_findings({"candidates": [candidate]})[0]["facts"] == a["checked_facts"]


async def test_blocked_profile_is_visible_before_any_model_call_and_resume_does_not_repeat(tmp_path):
    store = Store(tmp_path / "test.sqlite")
    store.save_settings(Settings(model="fixture"))
    brief = Brief(
        name="Юлия Тестенко",
        city="Example City",
        country="Ukraine",
        languages=["en"],
        budget=Budget(queries=4, pages=4, rounds=1),
    )
    job = store.create(brief)["id"]
    queries = []
    target = "https://www.linkedin.com/in/fictional-yulia-testenko"

    class Model:
        def __init__(self, _):
            pass

        async def complete(self, *args):
            raise AssertionError("Discovery must finish before model inference")

    class Search:
        def __init__(self, _):
            pass

        async def search(self, q, b):
            queries.append(q.query)
            if "Yulia Testenko" in q.query:
                return [
                    {
                        "url": target,
                        "title": "Yulia Testenko - Customer service | LinkedIn",
                        "snippet": "Public professional profile. No city stated.",
                    }
                ]
            return []

    class Reader:
        def __init__(self, *args, **kwargs):
            pass

        async def read(self, *args):
            raise ValueError("Site restricts automated reading in robots.txt")

    await Engine(store, Model, Search, Reader).run(job)
    d = store.detail(job)
    assert len(queries) == 4 and '"Yulia Testenko"' in queries
    assert d["leads"][0]["url"] == target
    assert d["leads"][0]["state"] == "unavailable"
    assert d["leads"][0]["snippet"]
    assert not d["candidates"] and not d["conclusion"]["promising_ids"]
    assert target in markdown(d) and "identity unverified" in markdown(d)
    await Engine(store, Model, Search, Reader).run(job)
    assert len(queries) == 4


def test_legacy_discovered_links_survive_without_snippets_and_obey_filters(tmp_path):
    store = Store(tmp_path / "test.sqlite")
    j = store.create(Brief(name="Alex Rowan", city="Example City"))["id"]
    url = "https://example.org/alex"
    store.enqueue(j, "fetch", url, {"url": url, "title": "Alex Rowan - Public portfolio", "depth": 1})
    with store.connect() as c:
        c.execute("UPDATE tasks SET state='failed' WHERE job_id=?", (j,))
    assert store.detail(j)["leads"][0]["url"] == url
    store.discover(j, {"url": url, "title": "Alex Rowan", "snippet": "Designer", "query": '"Alex Rowan"'})
    with store.connect() as c:
        r = c.execute("SELECT state,payload FROM tasks WHERE job_id=?", (j,)).fetchone()
    assert r["state"] == "failed" and json.loads(r["payload"])["depth"] == 1
    assert store.detail(j)["leads"][0]["snippet"] == "Designer"
    store.continue_research(j, Brief(name="Alex Rowan", exclude_domains=["example.org"]))
    assert not store.detail(j)["leads"]
