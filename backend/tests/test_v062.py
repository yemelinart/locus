import time

import pytest
from fastapi.testclient import TestClient
from locus.api import create_app
from locus.db import Store
from locus.discovery import portfolio, verification_queries
from locus.engine import Engine
from locus.models import Brief, Budget, Query, Settings
from test_core import FakeModel, FakeReader, FakeSearch

HEADERS = {"X-Locus-Request": "1"}


def test_live_clock_is_independent_of_activity_writes_and_pauses(tmp_path, monkeypatch):
    s = Store(tmp_path / "db.sqlite")
    j = s.create(Brief(name="Fictional Alex Rowan"))["id"]
    now = [100.0]
    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    s.update(j, status="running", active_seconds=12)
    s.begin_clock(j, 12, now[0])
    now[0] += 3.4
    s.activity(j, "reading", "A new page")
    assert s.job(j)["active_seconds"] == pytest.approx(15.4)
    now[0] += 2
    s.update(j, active_seconds=17.4)
    s.activity(j, "verifying", "New phase")
    assert s.detail(j)["active_seconds"] == pytest.approx(17.4)
    s.update(j, status="paused")
    s.end_clock(j)
    now[0] += 100
    assert s.job(j)["active_seconds"] == pytest.approx(17.4)
    assert Store(tmp_path / "db.sqlite").job(j)["active_seconds"] == pytest.approx(17.4)


@pytest.mark.parametrize("limit", ["time", "queries", "pages", "rounds"])
def test_exhausted_start_returns_actionable_error_and_extend_preserves_revision(tmp_path, limit):
    app = create_app(tmp_path, run_worker=False)
    s = app.state.store
    s.save_settings(Settings(model="fixture"))
    brief = Brief(name="Alex Rowan", budget=Budget(minutes=1, queries=1, pages=1, rounds=1))
    j = s.create(brief)["id"]
    if limit == "time":
        s.update(j, active_seconds=60.4)
    elif limit == "rounds":
        s.update(j, rounds=1)
    else:
        kind = "search" if limit == "queries" else "fetch"
        s.enqueue(
            j,
            kind,
            "old",
            {"query": "Alex Rowan"} if kind == "search" else {"url": "https://example.org/old"},
        )
        s.finish_task(s.task(j, kind)["id"])
    s.update(j, status="completed", reason="Exhausted fixture allowance")
    with TestClient(app) as client:
        response = client.post(f"/api/jobs/{j}/start", headers=HEADERS)
        assert response.status_code == 409 and "allowance exhausted" in response.json()["detail"]
        assert s.job(j)["status"] == "completed"
        response = client.post(
            f"/api/jobs/{j}/continue",
            headers=HEADERS,
            json={
                "brief": brief.model_dump(),
                "additional_budget": Budget().model_dump(),
                "start": True,
            },
        )
        assert response.status_code == 200
        detail = response.json()
        assert detail["status"] == "queued" and not detail["continuation"]["blocked_by"]
        assert detail["revision"] == 1 and len(detail["revisions"]) == 1


def test_network_limits_still_allow_pending_local_review(tmp_path):
    app = create_app(tmp_path, run_worker=False)
    s = app.state.store
    s.save_settings(Settings(model="fixture"))
    j = s.create(Brief(name="Alex Rowan", budget=Budget(queries=1, pages=1, rounds=1)))["id"]
    s.enqueue(j, "fetch", "https://example.org/a", {"url": "https://example.org/a"})
    s.finish_task(s.task(j, "fetch")["id"])
    s.enqueue(j, "analyze", "fixture", {"source_id": "fixture"})
    s.update(j, status="paused")
    with TestClient(app) as client:
        assert client.post(f"/api/jobs/{j}/start", headers=HEADERS).status_code == 200


async def test_extend_runs_saved_frontier_without_repeating_pages_or_invalidating_reviews(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    s.save_settings(Settings(model="fixture"))
    brief = Brief(name="Alex Rowan", languages=["en"], budget=Budget(queries=3, pages=1, rounds=2))
    j = s.create(brief)["id"]
    reads = []

    class Reader(FakeReader):
        async def read(self, url, *args):
            reads.append(url)
            return await super().read(url, *args)

    engine = Engine(s, FakeModel, FakeSearch, Reader)
    await engine.run(j)
    old = s.detail(j)
    assert len(old["candidates"]) == len(reads) == 1
    old_card = old["candidates"][0]
    with s.connect() as c:
        c.execute("UPDATE candidates SET status='confirmed' WHERE id=?", (old_card["id"],))
    extended = s.continue_research(
        j, Brief.model_validate(old["brief"]), Budget(queries=3, pages=2, rounds=2)
    )
    assert extended["revision"] == 1
    assert extended["queue"]["fetch"] == 1
    assert not extended["candidates"][0]["assessment"]["review_outdated"]
    await engine.run(j)
    final = s.detail(j)
    assert len(reads) == len(set(reads)) == 2
    assert len(final["candidates"]) == 2
    preserved = next(c for c in final["candidates"] if c["id"] == old_card["id"])
    assert preserved["verification"] == old_card["verification"]
    assert preserved["status"] == "confirmed" and not preserved["assessment"]["review_outdated"]
    keys = [q["key"] for q in final["queries"]]
    assert len(keys) == len(set(keys))


def test_missing_city_probes_run_before_generic_discovery_and_use_observed_host(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    brief = Brief(name="Alex Rowan", city="Dolynska", country="Ukraine")
    j = s.create(brief)["id"]
    s.enqueue(j, "search", "general", Query(query='"Alex Rowan" professional profiles').model_dump())
    probes = verification_queries(
        brief,
        {"name": "Alex Rowan"},
        "https://example.org/alex",
        [
            {"field": "city", "requested": "Dolynska", "relation": "unknown"},
        ],
    )
    for p in probes:
        s.enqueue(j, "search", p.query, p.model_dump())
    first = s.task(j, "search")["payload"]
    assert '"Dolynska" site:example.org' in first["query"]
    assert first["reason"].startswith("Investigate missing criterion:")


def test_later_pass_uses_remaining_spelling_hypotheses_without_repeating_queries():
    brief = Brief(name="Сергей Емелин", city="Александрия", country="Украина")
    initial = portfolio(brief, [], [], 2, first_round=True)
    later = portfolio(brief, [], [q.query for q in initial], 4, first_round=False)
    assert later and not {q.query for q in initial}.intersection(q.query for q in later)
