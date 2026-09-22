import json
import sqlite3
import zipfile
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from locus.api import create_app
from locus.archive import export_zip, project_path
from locus.db import Store, dump, now, uid
from locus.engine import Engine
from locus.models import Brief, Budget, EvidenceClue, Settings
from pypdf import PdfReader
from test_core import FakeModel, FakeReader, FakeSearch

HEADERS = {"X-Locus-Request": "1"}


def fixture(store):
    brief = Brief(
        name="Alex Rowan",
        evidence_clues=[
            EvidenceClue(kind="education", text="Example University"),
            EvidenceClue(kind="organization", text="Example Labs"),
        ],
    )
    job = store.create(brief)
    source_id, candidate_id = uid(), uid()
    value = {
        "name": "Alex Rowan",
        "description": "Public professional profile",
        "matches": ["Model thinks this is certain"],
        "contradictions": [],
        "facts": [
            {
                "category": "education",
                "statement": "Studied at Example University",
                "quote": "Alex Rowan studied at Example University.",
            },
            {
                "category": "organization",
                "statement": "Works at Example Labs",
                "quote": "Alex Rowan works at Example Labs.",
            },
        ],
    }
    with store.connect() as c:
        c.execute(
            "INSERT INTO sources(id,job_id,url,title,body,status,fetched_at) VALUES(?,?,?,?,?,'read',?)",
            (
                source_id,
                job["id"],
                "https://example.org/alex",
                "Public profile <script>alert(1)</script>",
                "RAW_PAGE_NOT_FOR_EXPORT",
                now(),
            ),
        )
        c.execute(
            "INSERT INTO candidates(id,job_id,source_id,value) VALUES(?,?,?,?)",
            (candidate_id, job["id"], source_id, dump(value)),
        )
    return job["id"], candidate_id, brief


def test_evidence_support_uses_quotes_not_model_opinions_and_missing_is_not_conflict(tmp_path):
    store = Store(tmp_path / "test.sqlite")
    job, cid, brief = fixture(store)
    assert store.detail(job)["candidates"][0]["assessment"]["level"] == "limited"
    brief.evidence_clues[1].text = "Different Labs"
    store.continue_research(job, brief)
    a = store.detail(job)["candidates"][0]["assessment"]
    assert a["level"] == "limited" and len(a["missing"]) == 2 and a["flags"] == []
    brief.evidence_clues = []
    store.continue_research(job, brief)
    assert store.detail(job)["candidates"][0]["assessment"]["level"] == "limited"
    brief.name = "Alex Row"
    store.continue_research(job, brief)
    assert store.detail(job)["candidates"][0]["assessment"]["level"] == "insufficient"


def test_filters_archive_and_restore_without_erasing_evidence(tmp_path):
    store = Store(tmp_path / "test.sqlite")
    job, cid, brief = fixture(store)
    brief.exclude_domains = ["example.org"]
    detail = store.continue_research(job, brief)
    assert detail["candidates"][0]["assessment"]["excluded"]
    assert detail["revisions"][0]["previous_assessments"][0]["assessment"]["level"] == "limited"
    brief.exclude_domains = []
    detail = store.continue_research(job, brief)
    assert not detail["candidates"][0]["assessment"]["excluded"]
    assert detail["candidates"][0]["id"] == cid
    assert len(detail["revisions"]) == 3


def test_revision_cancels_old_queue_and_adds_budget_to_work_done(tmp_path):
    store = Store(tmp_path / "test.sqlite")
    job, cid, brief = fixture(store)
    store.update(job, active_seconds=65, rounds=3, status="completed")
    store.enqueue(job, "search", "old", {"query": "Alex Rowan old"})
    store.finish_task(store.task(job, "search")["id"])
    store.enqueue(job, "search", "pending", {"query": "Alex Rowan pending"})
    store.enqueue(job, "fetch", "https://example.net/a", {"url": "https://example.net/a", "title": "New"})
    brief.context = "An additional public project clue"
    detail = store.continue_research(job, brief, Budget(minutes=10, queries=2, pages=3, rounds=1))
    assert detail["brief"]["budget"] == {"minutes": 12, "queries": 3, "pages": 3, "rounds": 4}
    assert [q["state"] for q in detail["queries"]] == ["done", "superseded"]
    assert store.enqueue(job, "search", "old", {"query": "Alex Rowan old"})
    assert store.enqueue(
        job, "fetch", "https://example.net/a", {"url": "https://example.net/a", "title": "New"}
    )
    assert store.task(job, "search")["revision"] == 2


def test_api_continuation_review_zip_and_deletion(tmp_path):
    app = create_app(tmp_path, run_worker=False)
    store = app.state.store
    job, cid, brief = fixture(store)
    with TestClient(app) as client:
        assert (
            client.post(
                f"/api/jobs/{job}/candidates/{cid}/review", headers=HEADERS, json={"status": "confirmed"}
            ).status_code
            == 200
        )
        brief.context = "An additional public project clue"
        body = {"brief": brief.model_dump(), "additional_budget": Budget().model_dump(), "start": False}
        r = client.post(f"/api/jobs/{job}/continue", headers=HEADERS, json=body)
        assert r.status_code == 200 and r.json()["candidates"][0]["assessment"]["review_outdated"]
        assert (
            client.post(
                f"/api/jobs/{job}/candidates/{cid}/review", headers=HEADERS, json={"status": "confirmed"}
            ).status_code
            == 200
        )
        assert not store.detail(job)["candidates"][0]["assessment"]["review_outdated"]
        r = client.get(f"/api/jobs/{job}/export?format=zip&lang=ru")
        assert r.status_code == 200
        with zipfile.ZipFile(BytesIO(r.content)) as z:
            names = z.namelist()
            assert all(n.startswith(f"locus-{job}/") and ".." not in n for n in names)
            assert len([n for n in names if "/sources/" in n]) == 1
            html = z.read(f"locus-{job}/index.html").decode()
            assert "<script>" not in html and "&lt;script&gt;" in html
            assert "RAW_PAGE_NOT_FOR_EXPORT" not in str(z.read(f"locus-{job}/research.json"))
            data = json.loads(z.read(f"locus-{job}/research.json"))
            assert len(data["revisions"]) == 2
            pdf = PdfReader(BytesIO(z.read(f"locus-{job}/report.pdf")))
            assert "Не входит в подходящие профили" in "".join(p.extract_text() for p in pdf.pages)
        folder = project_path(store, job)
        assert (folder / "index.html").exists()
        assert client.delete(f"/api/jobs/{job}", headers=HEADERS).status_code == 200
        assert not folder.exists() and client.get(f"/api/jobs/{job}").status_code == 404
        with pytest.raises(KeyError):
            store.sync_archive(job)
        assert not folder.exists()


def test_active_research_and_missing_model_are_not_mutated_by_continuation(tmp_path):
    app = create_app(tmp_path, run_worker=False)
    store = app.state.store
    job, cid, brief = fixture(store)
    body = {"brief": brief.model_dump(), "start": True}
    with TestClient(app) as client:
        assert client.post(f"/api/jobs/{job}/continue", json=body, headers=HEADERS).status_code == 409
        store.update(job, status="running")
        assert client.post(f"/api/jobs/{job}/continue", json=body, headers=HEADERS).status_code == 409
        assert client.delete(f"/api/jobs/{job}", headers=HEADERS).status_code == 409
        assert store.job(job)["revision"] == 1


def test_v2_migration_preserves_jobs_and_creates_backup(tmp_path):
    path = tmp_path / "test.sqlite3"
    store = Store(path)
    job, cid, brief = fixture(store)
    with store.connect() as c:
        c.execute("DROP TABLE revisions")
        c.execute("ALTER TABLE jobs DROP COLUMN revision")
        c.execute("ALTER TABLE candidates DROP COLUMN review_revision")
        c.execute("ALTER TABLE tasks DROP COLUMN revision")
        c.execute("PRAGMA user_version=2")
    store = Store(path)
    assert store.job(job)["revision"] == 1
    assert len(store.detail(job)["candidates"]) == 1
    assert store.detail(job)["revisions"][0]["number"] == 1
    with sqlite3.connect(path.with_suffix(".v2.backup.sqlite3")) as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == 2


async def test_completed_pipeline_can_run_same_query_with_new_criteria_without_duplicate_cards(tmp_path):
    store = Store(tmp_path / "test.sqlite")
    store.save_settings(Settings(model="test-local"))
    brief = Brief(name="Alex Rowan", languages=["en"], budget=Budget(queries=3, pages=5, rounds=3))
    job = store.create(brief)["id"]
    engine = Engine(store, FakeModel, FakeSearch, FakeReader)
    await engine.run(job)
    original = store.detail(job)
    brief.context = "New public project clue"
    store.continue_research(job, brief, Budget(queries=3, pages=5, rounds=3))
    await engine.run(job)
    detail = store.detail(job)
    assert detail["stats"]["queries"] == 2 * original["stats"]["queries"]
    assert len(detail["candidates"]) == len(original["candidates"]) == 2
    assert json.loads((project_path(store, job) / "research.json").read_text())["status"] == "completed"


def test_archive_refuses_symlink_escape(tmp_path):
    store = Store(tmp_path / "data" / "test.sqlite")
    job, cid, brief = fixture(store)
    outside = tmp_path / "outside"
    outside.mkdir()
    (project_path(store, job) / "sources").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic"):
        export_zip(store, job, "en")
    assert not list(outside.iterdir())


def test_archive_write_error_preserves_database_and_event_processing(tmp_path, monkeypatch):
    import locus.archive as archive

    store = Store(tmp_path / "test.sqlite")
    job = store.create(Brief(name="Alex Rowan"))["id"]

    def fail(*args):
        raise PermissionError("read only")

    monkeypatch.setattr(archive, "sync", fail)
    store.event(job, "Still researching")
    assert store.detail(job)["events"][0]["level"] == "warning"
    assert store.job(job)["name"] == "Alex Rowan"
    store.event(job, "Next step works")
    assert store.detail(job)["events"][0]["message"] == "Next step works"
