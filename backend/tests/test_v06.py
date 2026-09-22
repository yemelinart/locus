import json
import sqlite3

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from locus.api import create_app
from locus.db import Store, dump, now, uid
from locus.discovery import portfolio, verification_queries
from locus.models import Brief, Query, Settings
from locus.providers.search import Search
from locus.reports import markdown
from locus.trails import extract_links, relevant_links
from locus.verification import AUDIT_METHOD


def linked_fixture(store, conflict=False, linked=True, duplicate=False):
    brief = Brief(name="Alex Rowan", city="Dolynska", country="Ukraine", languages=["en"])
    job = store.create(brief)["id"]
    ids = []
    pages = [
        ("https://school.example.org/alex", "Alex Rowan studied design in Dolynska.", "city", "Dolynska"),
        ("https://work.example.org/alex", "Alex Rowan works as a designer in Ukraine.", "country", "Ukraine"),
    ]
    if conflict:
        pages[1] = (
            pages[1][0],
            "Alex Rowan has no biographical connection to Ukraine.",
            "country",
            "Ukraine",
        )
    for i, (url, body, field, observed) in enumerate(pages):
        sid, cid = uid(), uid()
        links = (
            [
                {
                    "url": pages[1][0],
                    "context": "Alex Rowan: professional portfolio",
                    "person": "",
                    "kind": "hyperlink",
                }
            ]
            if i == 0 and linked
            else []
        )
        with store.connect() as c:
            c.execute(
                "INSERT INTO sources(id,job_id,url,title,body,status,fetched_at,links,content_hash) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    sid,
                    job,
                    url,
                    "Public record " + str(i),
                    body,
                    "read",
                    now(),
                    dump(links),
                    "duplicate" if duplicate else str(i),
                ),
            )
            value = {
                "name": brief.name,
                "matches": [],
                "contradictions": [],
                "description": "",
                "facts": [{"category": "public_profile", "statement": body, "quote": body}],
            }
            c.execute(
                "INSERT INTO candidates(id,job_id,source_id,value) VALUES(?,?,?,?)",
                (cid, job, sid, dump(value)),
            )
        store.save_audit(
            cid,
            1,
            {
                "method": AUDIT_METHOD,
                "status": "reviewed",
                "name_relation": "same_spelling",
                "name_quote": body,
                "accepted_facts": [0],
                "supported": [],
                "conflicts": [],
                "identity_checks": [
                    {
                        "field": field,
                        "requested": observed,
                        "relation": "contradicts" if conflict and i else "supports",
                        "quote": body,
                        "observed": observed,
                    }
                ],
            },
            "fixture",
        )
        ids.append(cid)
    return job, ids, brief


def test_split_evidence_requires_explicit_link_and_preserves_provenance(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    job, ids, _ = linked_fixture(s)
    d = s.detail(job)
    assert len(d["linkage"]["proposals"]) == 1 and not d["linkage"]["groups"]
    assert all(c["assessment"]["identity_status"] == "unresolved" for c in d["candidates"])
    assert d["conclusion"]["state"] == "no_supported_findings"
    d = s.review_link(job, *ids, "confirmed")
    group = d["linkage"]["groups"][0]
    assert group["identity_status"] == "eligible"
    assert group["source_families"] == 2
    assert len({e["source_id"] for check in group["identity_checks"] for e in check["evidence"]}) == 2
    assert d["conclusion"]["linked_matches"] == 1
    assert d["conclusion"]["reviewed_claims"] == 2
    assert len(d["candidates"]) == 2  # No automatic/destructive merge.
    report = markdown(d)
    assert "Evidence across linked sources" in report
    assert "https://school.example.org/alex" in report and "https://work.example.org/alex" in report
    assert not s.review_link(job, *ids, "unreviewed")["linkage"]["groups"]


def test_same_name_without_observed_link_cannot_be_combined(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    job, ids, _ = linked_fixture(s, linked=False)
    assert s.detail(job)["linkage"]["proposals"] == []
    with pytest.raises(ValueError):
        s.review_link(job, *ids, "confirmed")


@pytest.mark.parametrize("change", ["reject", "revise", "exclude", "running"])
def test_link_decisions_cannot_override_boundaries(tmp_path, change):
    s = Store(tmp_path / "db.sqlite")
    job, ids, brief = linked_fixture(s)
    s.review_link(job, *ids, "confirmed")
    if change == "reject":
        with s.connect() as c:
            c.execute("UPDATE candidates SET status='rejected' WHERE id=?", (ids[1],))
    if change in {"revise", "exclude"}:
        if change == "exclude":
            brief.exclude_domains = ["work.example.org"]
        s.continue_research(job, brief)
    if change == "running":
        s.update(job, status="running")
        with pytest.raises(ValueError, match="Pause"):
            s.review_link(job, *ids, "confirmed")
    else:
        assert not s.detail(job)["linkage"]["groups"]
        assert s.detail(job)["conclusion"]["linked_matches"] == 0


def test_conflict_dominates_group_and_copied_sources_are_not_independent(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    job, ids, _ = linked_fixture(s, conflict=True, duplicate=True)
    d = s.review_link(job, *ids, "confirmed")
    assert d["linkage"]["groups"][0]["identity_status"] == "conflicting"
    assert d["linkage"]["groups"][0]["source_families"] == 1
    assert not d["conclusion"]["linked_matches"]


def test_html_trails_ignore_navigation_other_people_and_private_urls():
    html = """<nav><a href="/nav">Alex Rowan</a></nav><p>Alex Rowan: <a href="https://work.example.org/alex?utm_x=1">portfolio</a></p>
    <p>Other Person: <a href="https://other.example.org/">profile</a></p><p>Alex Rowan <a href="http://127.0.0.1/">local</a></p>
    <script type="application/ld+json">{"@type":"Person","name":"Alex Rowan","sameAs":["https://art.example.org/alex"]}</script>"""
    links = extract_links(BeautifulSoup(html, "html.parser"), "https://school.example.org/alex")
    selected = relevant_links(links, ["Alex Rowan"])
    assert {link["url"] for link in selected} == {
        "https://work.example.org/alex",
        "https://art.example.org/alex",
    }
    assert len(relevant_links(links, ["Alex Rowan"], exclude=["art.example.org"])) == 1
    assert not relevant_links(links, ["Nobody Else"])


def test_retrieval_can_cross_languages_without_relaxing_eligibility():
    b = Brief(name="Юлия Стешенко", city="Долинская", country="Украина", languages=["en", "ru", "uk"])
    planned = [Query(query='"Yulia Steshenko" Dolynska', language="en")]
    queries = portfolio(b, planned, [], 12, first_round=True)
    assert any(q.query == planned[0].query for q in queries)
    assert any(q.query == '"Юлия Стешенко"' for q in queries)
    assert any("Долинская" in q.query for q in queries)
    assert len({q.query.casefold() for q in queries}) == len(queries)
    previous = [q.query for q in queries]
    assert not portfolio(b, queries, previous, 12)
    followups = verification_queries(
        b,
        {"name": b.name},
        "https://example.org/profile",
        [{"field": "city", "requested": b.city, "relation": "unknown"}],
    )
    assert b.country not in followups[0].query  # Test one missing connection, not all at once.


async def test_provider_cooldown_skips_repeated_failures_and_preserves_audit(monkeypatch):
    settings = Settings(search_backends=["bing", "brave", "duckduckgo"])
    search = Search(settings)
    attempts = []

    async def request(text, query, brief, backend):
        attempts.append(backend)
        if backend != "duckduckgo":
            raise ValueError("Temporary outage")
        return [{"url": "https://example.org/", "title": "ok"}]

    monkeypatch.setattr(search, "_request", request)
    b = Brief(name="Alex Rowan")
    q = Query(query=b.name)
    for backend in ["bing", "brave"]:
        search._health_result(backend, "failed")
        search._health_result(backend, "failed")
    assert await search.search(q, b)
    assert attempts == ["duckduckgo"]
    assert search.last_audit[0]["status"] == "ok"
    search.restore_health([{"engine": "bing", "status": "ok", "at": now()}])
    assert search.health["bing"]["failures"] == 0


def test_schema_four_migration_and_revision_scoped_analysis(tmp_path):
    path = tmp_path / "db.sqlite"
    s = Store(path)
    job = s.create(Brief(name="Alex Rowan"))["id"]
    s.enqueue(job, "analyze", "source", {"source_id": "source"})
    s.finish_task(s.task(job, "analyze")["id"])
    with s.connect() as c:
        c.execute("DROP TABLE link_decisions")
        c.execute("ALTER TABLE sources DROP COLUMN links")
        c.execute("PRAGMA user_version=4")
    s = Store(path)
    with sqlite3.connect(path.with_suffix(".v4.backup.sqlite3")) as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == 4
    s.continue_research(job, Brief(name="Alex Rowan", city="Dolynska"))
    assert s.enqueue(job, "analyze", "source", {"source_id": "source"})
    assert s.task(job, "analyze")["revision"] == 2


def test_link_api_checks_project_membership_and_returns_updated_detail(tmp_path):
    app = create_app(tmp_path, run_worker=False)
    s = Store(tmp_path / "locus.sqlite3")
    job, ids, _ = linked_fixture(s)
    with TestClient(app) as client:
        r = client.post(
            f"/api/jobs/{job}/links/review",
            headers={"X-Locus-Request": "1"},
            json={"left_id": ids[0], "right_id": ids[1], "status": "confirmed"},
        )
        assert r.status_code == 200 and r.json()["linkage"]["groups"][0]["identity_status"] == "eligible"
        r = client.post(
            f"/api/jobs/{job}/links/review",
            headers={"X-Locus-Request": "1"},
            json={"left_id": ids[0], "right_id": uid(), "status": "confirmed"},
        )
        assert r.status_code == 422


def test_redirect_alias_can_support_a_proposal_but_not_an_automatic_merge(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    job, _, _ = linked_fixture(s)
    with s.connect() as c:
        c.execute(
            "UPDATE sources SET url_aliases=?,url=? WHERE job_id=? AND url=?",
            (
                dump(["https://work.example.org/alex"]),
                "https://portfolio.example.org/alex",
                job,
                "https://work.example.org/alex",
            ),
        )
    d = s.detail(job)
    assert len(d["linkage"]["proposals"]) == 1
    assert not d["linkage"]["groups"]


def test_same_domain_reading_does_not_starve_a_new_source(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    job = s.create(Brief(name="Alex Rowan"))["id"]
    with s.connect() as c:
        for i in range(3):
            c.execute(
                "INSERT INTO sources(id,job_id,url,title,status,fetched_at) VALUES(?,?,?,?,?,?)",
                (uid(), job, f"https://noisy.example.org/{i}", "Noisy", "read", now()),
            )
    s.enqueue(job, "fetch", "noisy", {"url": "https://noisy.example.org/more", "priority": 8})
    s.enqueue(job, "fetch", "new", {"url": "https://useful.example.org/profile", "priority": 3})
    assert s.task(job, "fetch")["key"] == "new"


def test_name_hypotheses_work_in_both_directions_without_becoming_facts():
    from locus.names import variants
    from locus.verification import useful_query

    for name, expected in [
        ("Sergey Yemelin", "Сергей Емелин"),
        ("Yulia Steshenko", "Юлія Стешенко"),
        ("Юлия Стешенко", "Yuliia Steshenko"),
    ]:
        brief = Brief(name=name)
        hypotheses = variants(brief)
        assert expected in {v["name"] for v in hypotheses}
        assert next(v for v in hypotheses if v["name"] == expected)["origin"] == "hypothesis"
        assert useful_query(Query(query=expected, language="uk"), brief)
        assert len(hypotheses) <= 24
        assert len(variants(brief.model_copy(update={"expand_names": False}))) == 1


def test_combining_records_does_not_erase_uncertain_name_attribution(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    job, ids, _ = linked_fixture(s)
    with s.connect() as c:
        audit = json.loads(
            c.execute("SELECT value FROM candidate_audits WHERE candidate_id=?", (ids[1],)).fetchone()[0]
        )
        audit["name_relation"] = "unclear"
        c.execute("UPDATE candidate_audits SET value=? WHERE candidate_id=?", (dump(audit), ids[1]))
    d = s.review_link(job, *ids, "confirmed")
    assert d["linkage"]["groups"][0]["identity_status"] == "unresolved"
    assert d["conclusion"]["linked_matches"] == 0


def test_named_profile_heading_allows_biography_navigation_only():
    html = '<h1>Alex Rowan — professional page</h1><p><a href="/bio">brief bio</a> <a href="/other">Other people</a> <a href="https://other.example.org/">portfolio</a></p>'
    links = extract_links(BeautifulSoup(html, "html.parser"), "https://example.org/")
    selected = relevant_links(links, ["Alex Rowan"])
    assert [link["url"] for link in selected] == ["https://example.org/bio"]
    assert selected[0]["kind"] == "profile_navigation"
    assert not relevant_links(links, ["Other Name"])


async def test_name_absence_skips_inference_and_revision_can_reconsider(tmp_path):
    from locus.engine import Engine
    from locus.models import Budget, Extraction, Plan

    class Reader:
        def __init__(self, *args):
            pass

        async def read(self, url, include, exclude):
            return {
                "url": url,
                "title": "Other profile",
                "body": "Other Person created a public design project.",
                "content_hash": "other",
                "links": [],
            }

    class Search:
        def __init__(self, *args):
            pass

        async def search(self, *args):
            return []

    class Model:
        extracts = 0

        def __init__(self, *args):
            pass

        async def complete(self, prompt, schema):
            if schema is Plan:
                return Plan(queries=[])
            assert schema is Extraction
            Model.extracts += 1
            return Extraction(candidates=[])

    s = Store(tmp_path / "db.sqlite")
    s.save_settings(Settings(model="fixture"))
    brief = Brief(
        name="Alex Rowan",
        seed_urls=["https://example.org/other"],
        budget=Budget(pages=1, queries=1, rounds=1),
    )
    job = s.create(brief)["id"]
    engine = Engine(s, Model, Search, Reader)
    await engine.run(job)
    assert Model.extracts == 0
    brief.name = "Other Person"
    s.continue_research(job, brief, Budget(pages=1, queries=1, rounds=1))
    await engine.run(job)
    assert Model.extracts == 1


def test_different_person_verdict_stays_a_conflict_even_when_geography_is_missing(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    job, ids, _ = linked_fixture(s)
    with s.connect() as c:
        audit = json.loads(
            c.execute("SELECT value FROM candidate_audits WHERE candidate_id=?", (ids[1],)).fetchone()[0]
        )
        audit["name_relation"] = "different"
        c.execute("UPDATE candidate_audits SET value=? WHERE candidate_id=?", (dump(audit), ids[1]))
    d = s.detail(job)
    candidate = next(c for c in d["candidates"] if c["id"] == ids[1])
    assert candidate["assessment"]["identity_status"] == "conflicting"
    assert candidate["assessment"]["level"] == "conflicting"
    assert s.review_link(job, *ids, "confirmed")["linkage"]["groups"][0]["identity_status"] == "conflicting"
