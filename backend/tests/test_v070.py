import asyncio
import socket

import pytest
from locus.db import Store
from locus.discovery import verification_queries
from locus.engine import Engine
from locus.identity import IdentityCheck, validate_checks
from locus.models import Brief, Budget, Extraction, Plan, Query, Settings
from locus.passages import evidence_passages
from locus.providers.local_model import ModelResponseError, parse_json, structured_response
from locus.providers.search import Search
from locus.retrieval import contextual_results, merge_results, score
from locus.verification import CandidateAudit, excerpt_for
from locus.web import PublicResolver, Reader, validate_url

GOOD = "Alex Rowan works as a designer in Dolynska, Ukraine."


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({}, "supports"),
        ({"passage_id": 11}, "unknown"),
        ({"quote": "Alex Rowan ... Dolynska, Ukraine."}, "unknown"),
        ({"same_subject": False}, "unknown"),
        ({"same_place": False}, "unknown"),
        ({"observed": "Moscow"}, "unknown"),
        ({"relation": "unknown"}, "unknown"),
    ],
)
def test_literal_passage_selection_keeps_identity_guards(changes, expected):
    brief = Brief(name="Alex Rowan", city="Dolynska", country="Ukraine")
    body = "Alex Rowan Photo: Dana Grey. Designer in Dolynska, Ukraine."
    passages = evidence_passages(body, brief, brief.name)
    assert passages and all(p["text"] in body for p in passages)
    check = IdentityCheck(
        **(
            dict(
                field="city",
                relation="supports",
                passage_id=0,
                observed="Dolynska",
                observed_country="Ukraine",
                same_subject=True,
                same_place=True,
            )
            | changes
        )
    )
    rows = validate_checks([check], brief, brief.name, body, body)
    assert rows[0]["relation"] == expected
    if expected == "supports":
        assert rows[0]["quote"] in body and rows[0]["quote"]
    assert rows[1]["relation"] == "unknown"  # A city check never fills another criterion.
    assert validate_checks([check, check], brief, brief.name, body, body)[0]["relation"] == "unknown"
    assert (
        validate_checks([check], brief, brief.name, "A different fetched page.", body)[0]["relation"]
        == "unknown"
    )


def test_passage_choices_cannot_bridge_omitted_text_or_borrow_another_name():
    brief = Brief(name="Alex Rowan", city="Dolynska")
    excerpt = "Alex Rowan\n[... omitted source text ...]\nDesigner in Dolynska."
    assert evidence_passages(excerpt, brief, brief.name) == []
    assert evidence_passages(GOOD, brief, "Dana Grey") == []


def test_year_only_search_and_late_birth_evidence_are_not_ignored():
    brief = Brief(name="Alex Rowan", year_from=1980, year_to=1985)
    assert not contextual_results([{"title": brief.name, "snippet": "Designer"}], brief)
    assert contextual_results([{"title": brief.name, "snippet": "Born 1982"}], brief)
    wrong_year = "Alex Rowan was born in 1970."
    body = ("Alex Rowan published another article. " + "Project description. " * 70) * 20
    body += wrong_year + " Supplementary material. " * 300
    excerpt = excerpt_for(body, brief, 4000)
    assert wrong_year in excerpt
    passage = next(p for p in evidence_passages(excerpt, brief, brief.name) if wrong_year in p["text"])
    check = IdentityCheck(
        field="birth_year",
        passage_id=passage["id"],
        relation="supports",
        observed="1970",
        birth_year=1970,
        same_subject=True,
    )
    assert validate_checks([check], brief, brief.name, body, excerpt)[0]["relation"] == "contradicts"


@pytest.mark.parametrize("line, expected", [("b. 1982", "supports"), ("published in 1982", "unknown")])
def test_year_reference_requires_a_birth_relation(line, expected):
    brief = Brief(name="Alex Rowan", year_from=1980, year_to=1985)
    body = f"Alex Rowan — {line}. Designer."
    check = IdentityCheck(
        field="birth_year",
        passage_id=0,
        relation="supports",
        observed="1982",
        birth_year=1982,
        same_subject=True,
    )
    assert validate_checks([check], brief, brief.name, body, body)[0]["relation"] == expected


@pytest.mark.parametrize("host", ["224.0.0.1", "239.255.255.250", "[ff02::1]"])
def test_multicast_is_not_a_public_web_source(host):
    with pytest.raises(ValueError):
        validate_url(f"http://{host}/")


async def test_public_hostname_cannot_resolve_to_multicast(monkeypatch):
    async def lookup(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("224.0.0.1", 443))]

    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", lookup)
    with pytest.raises(ValueError):
        await PublicResolver().resolve("example.org", 443)


def test_missing_city_probes_cannot_starve_other_criteria_or_repeat_exhausted_queries():
    brief = Brief(
        name="Alex Rowan",
        city="Dolynska",
        country="Ukraine",
        year_from=1980,
        year_to=1985,
        evidence_clues=[{"kind": "education", "text": f"Example School {i}"} for i in range(5)],
    )
    checks = [
        {"field": field, "requested": value, "relation": "unknown"}
        for field, value in [
            ("city", brief.city),
            ("country", brief.country),
            ("birth_year", "1980–1985"),
            *[(f"clue:{i}", c.text) for i, c in enumerate(brief.evidence_clues)],
        ]
    ]
    previous = []
    for _ in range(5):
        rows = verification_queries(brief, {"name": brief.name}, "https://example.org/alex", checks, previous)
        assert len(rows) <= 4
        assert not set(previous).intersection(q.query for q in rows)
        previous.extend(q.query for q in rows)
    assert any("born biography" in q for q in previous)
    assert all(any(c.text in q for q in previous) for c in brief.evidence_clues)
    assert any('"Ukraine"' in q for q in previous)


@pytest.mark.parametrize("value", ['{"queries": [', '{"queries":true}', "[]", None])
def test_invalid_model_output_is_typed_and_does_not_echo_content(value):
    with pytest.raises(ModelResponseError) as error:
        structured_response(value, Plan)
    assert "input_value" not in str(error.value)
    assert "Expecting" not in str(error.value)


def test_excerpts_preserve_tail_criterion_without_inventing_adjacency():
    brief = Brief(name="Alex Rowan", city="Dolynska", country="Украина")
    body = (
        " ".join([f"Alex Rowan published note {i}. " + "Project documentation. " * 90 for i in range(16)])
        + " "
        + GOOD
    )
    result = excerpt_for(body, brief, 4000)
    assert GOOD in result and len(result) <= 4000
    for passage in result.split("\n[... omitted source text ...]\n"):
        assert passage in body
    assert len(result) < len(body)
    assert "Ukraine" in result  # Translated country alias, not just raw input.


def test_discovery_signals_are_alias_aware_but_not_substring_identity():
    brief = Brief(name="Alex Rowan", city="Dolynska", country="Украина")
    relevant = {"url": "https://example.org/a?utm_source=x", "title": "Alex Rowan", "snippet": GOOD}
    weak = {"url": "https://example.org/a", "title": "Alex Rowan", "snippet": "Designer"}
    wrong = {"url": "https://other.example.org/", "title": "Other Person", "snippet": "Dolynska Ukraine"}
    assert contextual_results([relevant], brief)
    assert not contextual_results([weak, wrong], brief)
    assert not contextual_results([dict(weak, snippet="Designer in Ukraine")], brief)
    assert score(relevant, brief) > score(weak, brief)
    rows = merge_results([weak, relevant, wrong, {"url": "http://127.0.0.1/"}], brief, 4)
    assert len(rows) == 2 and rows[0]["snippet"] == GOOD
    assert not contextual_results(
        [{"title": "Alex Rowan", "snippet": "NotDolynska"}], Brief(name="Alex Rowan", city="Dolynska")
    )


async def test_weak_first_index_does_not_hide_a_better_second_index(monkeypatch):
    import locus.providers.search as module

    monkeypatch.setattr(module, "ENGINES", {"text": {"duckduckgo": object(), "brave": object()}})
    search = Search(Settings(search_backends=["duckduckgo", "brave"]))
    calls = []

    async def response(text, query, brief, backend):
        calls.append(backend)
        return [
            {
                "url": "https://example.org/" + backend,
                "title": "Alex Rowan",
                "snippet": GOOD if backend == "brave" else "Alex Rowan is a writer in Moscow.",
            }
        ]

    monkeypatch.setattr(search, "_request", response)
    rows = await search.search(
        Query(query='"Alex Rowan" Dolynska'), Brief(name="Alex Rowan", city="Dolynska")
    )
    assert calls == ["duckduckgo", "brave"] and rows[0]["url"].endswith("brave")
    assert [r["status"] for r in search.last_audit] == ["ok", "ok"]
    assert len(rows) == 2  # Unknown leads retained, never silently declared wrong.


class FixtureReader(Reader):
    html = f"<main><header><h1>Alex Rowan</h1></header><p>{GOOD}</p></main>"

    async def _get(self, url, *args, **kwargs):
        return 200, self.html, "text/html", url


async def test_reader_preserves_article_heading_and_short_public_profile():
    page = await FixtureReader().read("https://example.org/", [], [])
    assert page["body"].startswith("Alex Rowan") and GOOD in page["body"]
    reader = FixtureReader()
    reader.html = "<header>Site navigation</header><main><header><h1>Alex Rowan</h1></header><p>Designer in Dolynska, Ukraine.</p></main>"
    page = await reader.read("https://example.org/", [], [])
    assert "Site navigation" not in page["body"]
    assert page["body"] == "Alex Rowan Designer in Dolynska, Ukraine."


async def test_http_200_challenge_is_not_a_read_source():
    reader = FixtureReader()
    reader.html = (
        "<title>Just a moment...</title><main>Checking your browser. Alex Rowan " + "Wait. " * 30 + "</main>"
    )
    with pytest.raises(ValueError, match="проверку доступа"):
        await reader.read("https://example.org/", [], [])


class NoSearch:
    def __init__(self, _):
        pass

    async def search(self, *args):
        return []


class GoodModel:
    def __init__(self, _):
        pass

    async def complete(self, prompt, schema):
        if schema is Plan:
            return Plan(queries=[])
        if schema is Extraction:
            return Extraction(
                candidates=[
                    {
                        "name": "Alex Rowan",
                        "facts": [{"category": "public_profile", "statement": GOOD, "quote": GOOD}],
                    }
                ]
            )
        return CandidateAudit(
            name_relation="same_spelling",
            name_quote=GOOD,
            claims=[{"index": 0, "verdict": "supported"}],
            identity_checks=[
                {
                    "field": "city",
                    "relation": "supports",
                    "quote": GOOD,
                    "observed": "Dolynska",
                    "same_subject": True,
                    "same_place": True,
                }
            ],
        )


def store_job(tmp_path, urls):
    s = Store(tmp_path / "fixture.sqlite")
    s.save_settings(Settings(model="fixture"))
    j = s.create(
        Brief(
            name="Alex Rowan",
            city="Dolynska",
            languages=["en"],
            seed_urls=urls,
            budget=Budget(queries=1, pages=len(urls), rounds=1),
        )
    )["id"]
    return s, j


def test_budget_stop_with_pending_ai_remains_provisional(tmp_path):
    s, j = store_job(tmp_path, ["https://example.org/"])
    s.enqueue(j, "analyze", "saved-page", {"source_id": "saved-page"})
    s.update(j, status="completed")
    assert s.detail(j)["conclusion"]["provisional"]


async def test_bad_page_does_not_block_good_page_and_explicit_resume_retries_without_network(tmp_path):
    s, j = store_job(tmp_path, ["https://example.org/bad", "https://example.org/good"])
    failures = []

    class FlakyModel(GoodModel):
        async def complete(self, prompt, schema):
            if schema is Extraction and "https://example.org/bad" in prompt:
                failures.append(1)
                parse_json('{"candidates": [')
            return await super().complete(prompt, schema)

    await Engine(s, FlakyModel, NoSearch, FixtureReader).run(j)
    d = s.detail(j)
    assert len(failures) == 2
    assert len(d["conclusion"]["promising_ids"]) == 1
    assert d["retryable_model_steps"] == 1 and d["conclusion"]["provisional"]
    assert d["continuation"]["blocked_by"] == []  # Exhausted network does not block local recovery.
    s.recover()
    assert s.detail(j)["retryable_model_steps"] == 1  # Startup does not retry inference.

    class NoReader(FixtureReader):
        async def read(self, *args):
            raise AssertionError("Already fetched pages must not be fetched again")

    await Engine(s, GoodModel, NoSearch, NoReader).run(j)
    final = s.detail(j)
    assert final["retryable_model_steps"] == 0
    assert len(final["conclusion"]["promising_ids"]) == 2
    assert final["stats"]["pages"] == 2


async def test_repeated_format_failures_trip_circuit_and_never_assert_no_person(tmp_path):
    s, j = store_job(tmp_path, [f"https://example.org/{i}" for i in range(5)])
    attempts = []

    class BadModel(GoodModel):
        async def complete(self, prompt, schema):
            attempts.append(schema)
            raise ModelResponseError("fixture")

    await Engine(s, BadModel, NoSearch, FixtureReader).run(j)
    d = s.detail(j)
    assert len(attempts) == 6 and d["status"] == "paused"
    assert d["retryable_model_steps"] == 3 and not d["candidates"]
    assert d["queue"]["fetch"] == 2


async def test_format_retry_propagates_cancellation_with_pending_work(tmp_path):
    s, j = store_job(tmp_path, ["https://example.org/"])
    entered = asyncio.Event()

    class CancelModel(GoodModel):
        async def complete(self, prompt, schema):
            entered.set()
            await asyncio.Future()

    task = asyncio.create_task(Engine(s, CancelModel, NoSearch, FixtureReader).run(j))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    with s.connect() as c:
        row = c.execute("SELECT state FROM tasks WHERE kind='analyze'").fetchone()
    assert row[0] == "pending"
