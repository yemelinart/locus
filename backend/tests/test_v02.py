import json
import sqlite3
from io import BytesIO

import httpx
import pytest
from fastapi.testclient import TestClient
from locus.api import create_app
from locus.db import Store
from locus.models import Brief, Plan, Query, Settings
from locus.names import variants
from locus.providers.local_model import LocalModel
from locus.providers.search import Search
from locus.reports import analysis, pdf
from pypdf import PdfReader

HEADERS = {"X-Locus-Request": "1"}


def test_name_hypotheses_are_bounded_and_respect_opt_out():
    brief = Brief(name="Сергей Емелин", surname_change="possible")
    names = variants(brief)
    assert len(names) <= 24
    assert {"Sergey Yemelin", "Sergii Iemielin", "Сергій Ємєлін"} <= {n["name"] for n in names}
    assert all(n["origin"] == "hypothesis" for n in names[1:])
    assert variants(brief.model_copy(update={"expand_names": False})) == [
        {"name": brief.name, "origin": "supplied", "reason": "Original name"}
    ]
    known = variants(Brief(name="Jane Smith", previous_names=["Jane Rowan"], surname_change="known"))
    assert [v["name"] for v in known] == ["Jane Smith", "Jane Rowan"]


def test_v1_database_migrates_with_backup_without_losing_jobs(tmp_path):
    path = tmp_path / "old.sqlite3"
    store = Store(path)
    job = store.create(Brief(name="Alex Rowan"))
    with store.connect() as c:
        c.execute("DROP TABLE search_runs")
        c.execute("PRAGMA user_version=1")
        c.execute("UPDATE jobs SET brief=?", (json.dumps({"name": "Alex Rowan", "languages": ["ru", "en"]}),))
    migrated = Store(path)
    assert migrated.job(job["id"])["brief"]["expand_names"] is True
    backup = path.with_suffix(".v1.backup.sqlite3")
    assert backup.exists()
    with sqlite3.connect(backup) as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == 1
    with migrated.connect() as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == 5
    assert migrated.detail(job["id"])["search_runs"] == []


async def test_native_reasoning_passes_only_reported_capability(monkeypatch):
    packets = []

    async def handler(request):
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "type": "llm",
                            "key": "test",
                            "capabilities": {
                                "reasoning": {"allowed_options": ["off", "xhigh"], "default": "off"}
                            },
                        }
                    ]
                },
            )
        packets.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "output": [
                    {"type": "reasoning", "content": "not retained"},
                    {"type": "message", "content": '{"queries":[]}'},
                ]
            },
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)
    )
    model = LocalModel(
        Settings(model="test", inference_mode="lmstudio", reasoning="xhigh", response_language="en")
    )
    assert (await model.complete("Plan", Plan)).queries == []
    assert packets[0]["reasoning"] == "xhigh"
    assert packets[0]["integrations"] == [] and packets[0]["store"] is False
    assert "English" in packets[0]["system_prompt"]
    model.settings.reasoning = "medium"
    with pytest.raises(ValueError, match="does not expose"):
        await model.complete("Plan", Plan)
    assert len(packets) == 1


async def test_search_rotation_and_failures_have_real_audit(monkeypatch):
    import locus.providers.search as module

    monkeypatch.setattr(module, "ENGINES", {"text": {"duckduckgo": object(), "brave": object()}})
    settings = Settings(search_backends=["bing", "duckduckgo", "brave"])
    search = Search(settings)
    called = []

    async def request(text, query, brief, backend):
        called.append(backend)
        if backend == "duckduckgo":
            raise ValueError("temporarily unavailable")
        return [{"url": "https://example.org", "title": "Example"}]

    monkeypatch.setattr(search, "_request", request)
    await search.search(Query(query="Alex Rowan"), Brief(name="Alex Rowan"))
    assert called == ["duckduckgo", "brave"]
    assert [r["status"] for r in search.last_audit] == ["failed", "ok"]
    assert search.last_audit[-1]["result_count"] == 1
    called.clear()
    await search.search(Query(query="Alex Rowan work"), Brief(name="Alex Rowan"))
    # A nonempty response without even the requested name warrants another index.
    assert called == ["brave", "duckduckgo"]
    search.settings = Settings(search_backends=["bing"])
    with pytest.raises(ValueError, match="No selected"):
        await search.search(Query(query="Alex Rowan"), Brief(name="Alex Rowan"))


def test_analysis_does_not_invent_engine_activity(tmp_path):
    store = Store(tmp_path / "test.sqlite3")
    job = store.create(Brief(name="Alex Rowan"))
    assert analysis(store.detail(job["id"]))["engines"] == []
    store.record_search(
        job["id"],
        "query1",
        [
            {
                "engine": "brave",
                "status": "ok",
                "result_count": 3,
                "seconds": 0.5,
                "at": "2026-09-21T00:00:00Z",
            }
        ],
    )
    result = analysis(store.detail(job["id"]))
    assert result["engine_coverage_known"] is True
    assert result["engines"][0]["attempts"] == 1
    assert result["engines"][0]["results"] == 3


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_pdf_contains_structured_readable_text_and_escaped_input(tmp_path, lang):
    store = Store(tmp_path / "test.sqlite3")
    job = store.create(Brief(name="Сергей <test> Yemelin", context="A&B <script>literal text</script>"))
    doc = PdfReader(BytesIO(pdf(store.detail(job["id"]), lang)))
    text = "\n".join(p.extract_text() for p in doc.pages)
    assert "Сергей <test> Yemelin" in text
    assert "A&B <script>literal text</script>" in text
    assert ("Overview" if lang == "en" else "Обзор") in text
    assert len(doc.pages) >= 1


def test_export_and_analysis_routes_and_unknown_format(tmp_path):
    with TestClient(create_app(tmp_path, run_worker=False)) as client:
        job = client.post("/api/jobs", headers=HEADERS, json={"name": "Example Rowan"}).json()
        prefix = "/api/jobs/" + job["id"]
        assert client.get(prefix + "/export?format=exe").status_code == 422
        assert client.get(prefix + "/export?format=pdf").headers["content-type"] == "application/pdf"
        assert "analysis" in client.get(prefix + "/export?format=json").json()
        assert client.get(prefix + "/analysis").json()["engine_coverage_known"] is False
        assert client.post("/api/names/preview", headers=HEADERS, json={"name": "Сергей Емелин"}).json()[
            "variants"
        ]
        assert any(e["id"] == "google" for e in client.get("/api/search/catalog").json())
