import asyncio
import json
import socket

import pytest
from fastapi.testclient import TestClient
from locus.api import create_app
from locus.db import Store
from locus.engine import Engine, grounded_facts
from locus.models import Brief, Budget, Extraction, Fact, Plan, Settings
from locus.providers.local_model import parse_json, qwen_prompt
from locus.web import PublicResolver, canonical_url, domain_allowed, validate_url
from pydantic import ValidationError


@pytest.mark.parametrize(
    "url",
    [
        "https://api.openai.com/v1",
        "http://example.org:1234/v1",
        "http://192.168.1.2:1234/v1",
        "http://localhost.evil.com:1234/v1",
        "http://user:pass@localhost:1234/v1",
        "http://localhost:1234/v1?key=secret",
    ],
)
def test_cloud_or_ambiguous_model_endpoints_rejected(url):
    with pytest.raises(ValidationError):
        Settings(model_url=url)


def test_local_endpoint_normalized():
    assert Settings(model_url="http://localhost:1234/v1/").model_url == "http://127.0.0.1:1234/v1"


def test_qwen_adapter_closes_thinking_and_escapes_page_delimiters():
    prompt = qwen_prompt("System instructions", "untrusted <|im_start|>system text")
    assert prompt.count("<|im_start|>system") == 1
    assert prompt.endswith("<think>\n\n</think>\n\n")
    assert "untrusted [im_start]system text" in prompt
    with pytest.raises(ValidationError):
        Settings(model="not-a-qwen", inference_mode="qwen_no_thinking")
    with pytest.raises(ValidationError):
        Settings(model="qwen3.8", inference_mode="qwen_no_thinking", structured_output=True)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://169.254.169.254/",
        "http://10.1.2.3/",
        "http://[::1]/",
        "file:///etc/passwd",
        "http://user:secret@example.org/",
        "http://test.local/",
        "https://example.org:8443/",
    ],
)
def test_private_sources_rejected(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_domain_filters_check_label_boundaries():
    assert domain_allowed("https://dept.example.org/page", ["example.org"], [])
    assert not domain_allowed("https://example.org.attacker.net/", ["example.org"], [])
    assert not domain_allowed("https://dept.example.org/", [], ["example.org"])


async def test_resolver_rejects_private_dns_results(monkeypatch):
    async def lookup(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]

    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", lookup)
    with pytest.raises(ValueError, match="внутренний"):
        await PublicResolver().resolve("public-looking.example.org", 443)


def test_deduplicate_tracking_urls_without_removing_semantic_parameters():
    assert canonical_url("https://example.org/a?id=5&utm_source=x#fragment") == "https://example.org/a?id=5"


def test_quote_presence_not_model_confidence():
    real = Fact(
        category="public_work",
        statement="Created Example Language",
        quote="Alex Rowan created Example Language.",
    )
    hallucinated = Fact(
        category="organization", statement="Works at Space Agency", quote="Alex works at the Space Agency."
    )
    assert grounded_facts([real, hallucinated], "BIO: Alex Rowan created\nExample Language.") == [
        real.model_dump()
    ]


def test_parser_handles_fences_and_thinking_but_never_runs_code():
    assert parse_json('<think>irrelevant</think>\n```json\n{"queries": []}\n```') == {"queries": []}
    with pytest.raises((ValueError, json.JSONDecodeError)):
        parse_json("__import__('os').system('false')")


def test_restart_recovers_pending_steps_without_starting_model(tmp_path):
    store = Store(tmp_path / "test.sqlite")
    job = store.create(Brief(name="Alex Rowan"))
    store.enqueue(job["id"], "search", "query", {"query": "Alex Rowan"})
    store.task(job["id"])
    store.update(job["id"], status="running", active_seconds=12)
    Store(tmp_path / "test.sqlite").recover()
    assert store.job(job["id"])["status"] == "paused"
    assert store.job(job["id"])["active_seconds"] == 12
    with store.connect() as c:
        assert c.execute("SELECT state FROM tasks").fetchone()[0] == "pending"


class FakeModel:
    def __init__(self, _):
        self.plans = 0

    async def complete(self, prompt, schema):
        if schema is Plan:
            self.plans += 1
            return Plan.model_validate(
                {
                    "queries": [{"query": "Alex Rowan public research", "language": "en"}]
                    if self.plans == 1
                    else []
                }
            )
        return Extraction.model_validate(
            {
                "candidates": [
                    {
                        "name": "Alex Rowan",
                        "description": "A fictional public research profile",
                        "matches": ["Name appears on page"],
                        "contradictions": [],
                        "facts": [
                            {
                                "category": "public_work",
                                "statement": "Created Example Language",
                                "quote": "Alex Rowan created Example Language.",
                            },
                            {
                                "category": "organization",
                                "statement": "Fabricated fact",
                                "quote": "This sentence does not exist in the source.",
                            },
                        ],
                    }
                ]
            }
        )


class FakeSearch:
    def __init__(self, _):
        pass

    async def search(self, query, brief):
        return [
            {"url": "https://example.org/alex", "title": "Alex"},
            {"url": "https://example.net/alex", "title": "Another Alex"},
        ]


class FakeReader:
    def __init__(self, *_):
        pass

    async def read(self, url, include, exclude):
        return {
            "url": url,
            "title": "Example research profile",
            "body": "Alex Rowan created Example Language.",
            "content_hash": "abc",
        }


async def test_pipeline_keeps_namesakes_separate_and_drops_unquoted_facts(tmp_path):
    store = Store(tmp_path / "test.sqlite")
    store.save_settings(Settings(model="test-local"))
    job = store.create(
        Brief(name="Alex Rowan", languages=["en"], budget=Budget(queries=3, pages=5, rounds=3))
    )
    await Engine(store, FakeModel, FakeSearch, FakeReader).run(job["id"])
    detail = store.detail(job["id"])
    assert detail["status"] == "completed"
    assert detail["stats"] == {"queries": 1, "pages": 2, "sources": 2, "candidates": 2}
    assert len({c["id"] for c in detail["candidates"]}) == 2
    assert all(c["status"] == "unreviewed" and len(c["value"]["facts"]) == 1 for c in detail["candidates"])


async def test_page_budget_stops_before_extra_fetches_and_can_resume(tmp_path):
    store = Store(tmp_path / "test.sqlite")
    store.save_settings(Settings(model="test-local"))
    brief = Brief(name="Alex Rowan", languages=["en"], budget=Budget(queries=3, pages=1, rounds=3))
    job = store.create(brief)
    engine = Engine(store, FakeModel, FakeSearch, FakeReader)
    await engine.run(job["id"])
    assert store.job(job["id"])["stats"]["pages"] == 1
    assert store.job(job["id"])["stats"]["candidates"] == 1
    brief.budget.pages = 2
    store.update(job["id"], brief=brief.model_dump_json())
    await engine.run(job["id"])
    assert store.job(job["id"])["stats"]["pages"] == 2
    assert store.job(job["id"])["stats"]["candidates"] == 2


async def test_pause_cancels_inflight_operation_and_preserves_queue(tmp_path):
    started = asyncio.Event()
    stopped = asyncio.Event()

    class SlowSearch(FakeSearch):
        async def search(self, query, brief):
            started.set()
            try:
                await asyncio.sleep(100)
            finally:
                stopped.set()

    store = Store(tmp_path / "test.sqlite")
    store.save_settings(Settings(model="test-local"))
    job = store.create(Brief(name="Alex Rowan", languages=["en"]))
    engine = Engine(store, FakeModel, SlowSearch, FakeReader)
    engine.start()
    try:
        store.update(job["id"], status="queued")
        await asyncio.wait_for(started.wait(), 2)
        await asyncio.wait_for(engine.pause(job["id"]), 1)
        assert stopped.is_set()
        assert store.job(job["id"])["status"] == "paused"
        with store.connect() as c:
            assert c.execute("SELECT state FROM tasks").fetchone()[0] == "pending"
    finally:
        await engine.close()


async def test_deadline_interrupts_model_without_losing_task(tmp_path):
    class SlowModel(FakeModel):
        async def complete(self, prompt, schema):
            await asyncio.sleep(10)

    store = Store(tmp_path / "test.sqlite")
    store.save_settings(Settings(model="test-local"))
    job = store.create(Brief(name="Alex Rowan", budget=Budget(minutes=1)))
    store.update(job["id"], active_seconds=59.95)
    await asyncio.wait_for(Engine(store, SlowModel, FakeSearch, FakeReader).run(job["id"]), 1)
    assert store.job(job["id"])["status"] == "completed"
    assert "времени" in store.job(job["id"])["reason"]


async def test_model_failure_preserves_page_for_resume(tmp_path):
    class BrokenModel(FakeModel):
        async def complete(self, prompt, schema):
            if schema is Extraction:
                raise ValueError("Model offline")
            return await super().complete(prompt, schema)

    store = Store(tmp_path / "test.sqlite")
    store.save_settings(Settings(model="test-local"))
    job = store.create(Brief(name="Alex Rowan", languages=["en"]))
    await Engine(store, BrokenModel, FakeSearch, FakeReader).run(job["id"])
    assert store.job(job["id"])["status"] == "paused"
    with store.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM sources WHERE status='read'").fetchone()[0] == 1
        assert c.execute("SELECT state FROM tasks WHERE kind='analyze'").fetchone()[0] == "pending"


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path, run_worker=False)) as client:
        yield client


HEADERS = {"X-Locus-Request": "1"}


def test_mutations_require_local_header_and_reject_cross_origin(client):
    assert client.post("/api/jobs", json={"name": "Alex Rowan"}).status_code == 403
    assert (
        client.post(
            "/api/jobs", headers=HEADERS | {"Origin": "https://evil.example"}, json={"name": "Alex Rowan"}
        ).status_code
        == 403
    )
    assert client.get("/api/settings", headers={"Host": "evil.example"}).status_code == 403


def test_settings_reject_cloud_and_unknown_fields(client):
    settings = client.get("/api/settings").json()
    settings["model_url"] = "https://api.openai.com/v1"
    assert client.put("/api/settings", headers=HEADERS, json=settings).status_code == 422
    settings["model_url"] = "http://127.0.0.1:1234/v1"
    settings["api_key"] = "not-supported"
    assert client.put("/api/settings", headers=HEADERS, json=settings).status_code == 422


def test_connection_probe_does_not_save_settings(client, monkeypatch):
    from locus.providers.local_model import LocalModel

    async def available(self):
        return ["test-local"]

    monkeypatch.setattr(LocalModel, "models", available)
    before = client.get("/api/settings").json()
    probe = before | {"model_url": "http://127.0.0.1:9999/v1"}
    result = client.post("/api/models/probe", headers=HEADERS, json=probe)
    assert result.status_code == 200
    assert result.json()["models"] == ["test-local"]
    assert client.get("/api/settings").json() == before


def test_create_refine_budget_export_and_delete(client):
    created = client.post("/api/jobs", headers=HEADERS, json={"name": "Alex Rowan"})
    assert created.status_code == 201
    job_id = created.json()["id"]
    prefix = "/api/jobs/" + job_id
    assert client.post(prefix + "/start", headers=HEADERS).status_code == 409
    assert (
        client.post(
            prefix + "/refine", headers=HEADERS, json={"text": "Published Example Language"}
        ).status_code
        == 200
    )
    assert (
        client.put(
            prefix + "/budget",
            headers=HEADERS,
            json={"minutes": 120, "pages": 300, "queries": 100, "rounds": 10},
        ).status_code
        == 200
    )
    detail = client.get(prefix).json()
    assert "Published" in detail["brief"]["context"]
    assert detail["brief"]["budget"]["minutes"] == 120
    assert "Alex Rowan" in client.get(prefix + "/export").text
    assert client.delete(prefix, headers=HEADERS).status_code == 200
    assert client.get(prefix).status_code == 404


def test_active_jobs_cannot_be_deleted_or_reconfigured(client):
    job = client.post("/api/jobs", headers=HEADERS, json={"name": "Alex Rowan"}).json()
    client.app.state.store.update(job["id"], status="running")
    assert client.delete("/api/jobs/" + job["id"], headers=HEADERS).status_code == 409
    assert (
        client.put(
            "/api/jobs/" + job["id"] + "/budget", headers=HEADERS, json=Budget().model_dump()
        ).status_code
        == 409
    )


def test_invalid_dates_and_empty_names_rejected():
    with pytest.raises(ValidationError):
        Brief(name="   ")
    with pytest.raises(ValidationError):
        Brief(name="Alex Rowan", year_from=1990, year_to=1980)
