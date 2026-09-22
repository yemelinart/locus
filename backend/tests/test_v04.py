import asyncio
import sqlite3

import pytest
from locus.db import Store, dump, now, uid
from locus.engine import Engine
from locus.models import Brief, Budget, EvidenceClue, Query, Settings
from locus.reports import markdown
from locus.verification import CandidateAudit, ObservationReview, excerpt_for, useful_query, validate_audit
from test_core import FakeModel, FakeReader, FakeSearch


def fixture():
    brief = Brief(
        name="Alex Rowan",
        languages=["en"],
        evidence_clues=[
            EvidenceClue(kind="education", text="Example University"),
            EvidenceClue(kind="organization", text="Example Labs"),
        ],
    )
    body = "Alex Rowan studied at Example University. Alex Rowan works at Example Labs. Maya Chen works at Other Labs."
    value = {
        "name": "Alex Rowan",
        "description": "Unverified prose",
        "matches": [],
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
            {
                "category": "organization",
                "statement": "Works at Other Labs",
                "quote": "Maya Chen works at Other Labs.",
            },
        ],
    }
    audit = CandidateAudit(
        name_relation="same_spelling",
        name_quote=value["facts"][0]["quote"],
        claims=[
            {"index": 0, "verdict": "supported"},
            {"index": 1, "verdict": "supported"},
            {"index": 2, "verdict": "unsupported"},
        ],
        clues=[
            {"index": 0, "relation": "supports", "quote": value["facts"][0]["quote"]},
            {"index": 1, "relation": "supports", "quote": value["facts"][1]["quote"]},
        ],
        note="The quoted education and organisation match the supplied clues. Please verify the profile.",
        note_facts=[0, 1],
    )
    return brief, body, value, audit


def saved(store):
    brief, body, value, audit = fixture()
    job = store.create(brief)["id"]
    sid, cid = uid(), uid()
    with store.connect() as c:
        c.execute(
            "INSERT INTO sources(id,job_id,url,title,body,status,fetched_at) VALUES(?,?,?,?,?,'read',?)",
            (sid, job, "https://example.org/alex", "Public profile", body, now()),
        )
        c.execute(
            "INSERT INTO candidates(id,job_id,source_id,value) VALUES(?,?,?,?)", (cid, job, sid, dump(value))
        )
    return job, cid, brief, validate_audit(audit, value, brief, body, body)


def test_reviewed_profile_omits_wrong_subject_and_invalid_paraphrase(tmp_path):
    store = Store(tmp_path / "test.sqlite")
    job, cid, brief, review = saved(store)
    before = store.detail(job)
    assert before["conclusion"]["state"] == "no_supported_findings"
    assert before["candidates"][0]["assessment"]["level"] == "limited"
    store.save_audit(cid, 1, review, "fixture-model")
    after = store.detail(job)
    assert after["conclusion"]["state"] == "possible"
    assert after["conclusion"]["reviewed_claims"] == 2
    a = after["candidates"][0]["assessment"]
    assert a["level"] == "strong" and len(a["checked_facts"]) == 2
    report = markdown(after)
    assert "Works at Other Labs" not in report and "Unverified prose" not in report
    assert "https://example.org/alex" in report and "Example University" in report
    brief.evidence_clues[0].text = "Different University"
    store.continue_research(job, brief)
    stale = store.detail(job)
    assert stale["candidates"][0]["assessment"]["audit_outdated"]
    assert stale["conclusion"]["reviewed_claims"] == 0
    assert "Works at Example Labs" not in markdown(stale)


def test_fabricated_references_and_cross_person_name_fail_closed():
    brief, body, value, audit = fixture()
    audit.name_quote = "Invented name quote: Alex Rowan studied at Real University."
    audit.clues[0].quote = "Invented clue quote: Alex Rowan studied at Example University."
    audit.note_facts = [9]
    review = validate_audit(audit, value, brief, body, body)
    assert review["name_quote"] == "" and review["note"] == ""
    assert len(review["supported"]) == 1
    value["name"] = "Maya Chen"
    audit.name_quote = "Alex Rowan studied at Example University."
    assert not validate_audit(audit, value, brief, body, body)["name_quote"]


def test_confirmed_overview_requires_current_manual_and_semantic_review(tmp_path):
    store = Store(tmp_path / "test.sqlite")
    job, cid, brief, review = saved(store)
    heading = "Your confirmed profile — public work and education"
    with store.connect() as c:
        c.execute("UPDATE candidates SET status='confirmed' WHERE id=?", (cid,))
    assert heading not in markdown(store.detail(job))
    store.save_audit(cid, 1, review, "fixture-model")
    report = markdown(store.detail(job))
    profile = report.split(heading)[1].split("02 / Starting information")[0]
    assert "Works at Example Labs" in profile and "https://example.org/alex" in profile
    assert "Other Labs" not in profile
    with store.connect() as c:
        c.execute("UPDATE candidates SET status='rejected' WHERE id=?", (cid,))
    assert heading not in markdown(store.detail(job))
    with store.connect() as c:
        c.execute("UPDATE candidates SET status='confirmed' WHERE id=?", (cid,))
    store.continue_research(job, brief)
    store.save_audit(cid, 2, review, "fixture-model")
    assert heading not in markdown(store.detail(job))
    with store.connect() as c:
        c.execute("UPDATE candidates SET review_revision=2 WHERE id=?", (cid,))
    assert heading in markdown(store.detail(job))
    brief.exclude_domains = ["example.org"]
    store.continue_research(job, brief)
    store.save_audit(cid, 3, review, "fixture-model")
    with store.connect() as c:
        c.execute("UPDATE candidates SET review_revision=3 WHERE id=?", (cid,))
    assert heading not in markdown(store.detail(job))


def test_duplicate_ids_uncertainty_and_missing_are_not_support():
    brief, body, value, audit = fixture()
    audit.claims.append(audit.claims[0])
    audit.clues.append(audit.clues[1])
    review = validate_audit(audit, value, brief, body, body)
    assert review["accepted_facts"] == [1]
    assert review["supported"] == [] and review["note"] == ""
    assert review["conflicts"] == []


def test_model_approval_cannot_join_unrelated_source_sentences():
    brief, _, value, audit = fixture()
    body = "Alex Rowan completed Art School. Bachelor of Economics & Specialist degree in Arts."
    value["facts"] = [
        {
            "category": "education",
            "statement": "Graduated from Art School with a Bachelor of Economics and Specialist degree in Arts",
            "quote": body,
        }
    ]
    audit.name_quote = body
    audit.claims = audit.claims[:1]
    audit.clues = []
    audit.note_facts = [0]
    result = validate_audit(audit, value, brief, body, body)
    assert result["accepted_facts"] == [] and result["note"] == ""
    value["facts"][0]["statement"] = "Alex Rowan completed Art School"
    assert validate_audit(audit, value, brief, body, body)["accepted_facts"] == [0]


def test_conflict_requires_a_real_quote_and_is_not_missing(tmp_path):
    store = Store(tmp_path / "test.sqlite")
    job, cid, brief, review = saved(store)
    review["conflicts"] = [
        {
            "kind": "education",
            "text": "Example University",
            "index": 0,
            "quote": "Alex Rowan never attended Example University.",
        }
    ]
    # Persistence receives only validator output in production; test the assessment's handling here.
    store.save_audit(cid, 1, review, "fixture-model")
    assert store.detail(job)["candidates"][0]["assessment"]["level"] == "conflicting"
    brief, body, value, audit = fixture()
    audit.clues[0].relation = "contradicts"
    audit.clues[0].quote = "Alex Rowan never attended Example University."
    assert validate_audit(audit, value, brief, body, body)["conflicts"] == []


def test_query_validation_stays_with_target_and_languages():
    brief, *_ = fixture()
    assert useful_query(Query(query='"Alex Rowan" Example University', language="en"), brief)
    assert not useful_query(Query(query="Maya Chen private address", language="en"), brief)
    assert not useful_query(Query(query="Alex Rowan", language="ja"), brief)


def test_relevant_name_at_page_tail_is_not_truncated():
    brief, body, *_ = fixture()
    long = ("Navigation and unrelated introduction. " * 1800) + body
    excerpt = excerpt_for(long, brief, 4000)
    assert "Alex Rowan studied at Example University." in excerpt
    assert len(excerpt) <= 4000


def test_no_accessible_sources_not_reported_as_success(tmp_path):
    store = Store(tmp_path / "test.sqlite")
    job = store.create(Brief(name="Alex Rowan"))["id"]
    store.update(job, status="completed")
    with store.connect() as c:
        c.execute(
            "INSERT INTO sources(id,job_id,url,title,status,error,fetched_at) VALUES(?,?,?,?,?,?,?)",
            (uid(), job, "https://example.org/alex", "Profile", "unavailable", "Login required", now()),
        )
    result = store.detail(job)
    assert result["conclusion"]["state"] == "no_accessible_sources"
    assert result["conclusion"]["unavailable_sources"] == 1
    assert result["conclusion"]["reviewed_claims"] == 0


def test_schema_three_backup_and_future_version_rejection(tmp_path):
    path = tmp_path / "test.sqlite"
    store = Store(path)
    job = store.create(Brief(name="Alex Rowan"))["id"]
    with store.connect() as c:
        c.execute("DROP TABLE candidate_audits")
        c.execute("ALTER TABLE jobs DROP COLUMN activity")
        c.execute("PRAGMA user_version=3")
    store = Store(path)
    assert store.job(job)["activity"] == {}
    with sqlite3.connect(path.with_suffix(".v3.backup.sqlite3")) as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == 3
    with store.connect() as c:
        c.execute("PRAGMA user_version=5")
    with pytest.raises(RuntimeError):
        Store(path)


async def test_pause_during_semantic_review_resumes_without_duplicates(tmp_path):
    started = asyncio.Event()

    class SlowAudit(FakeModel):
        async def complete(self, prompt, schema):
            if schema is CandidateAudit:
                started.set()
                await asyncio.sleep(60)
            return await super().complete(prompt, schema)

    store = Store(tmp_path / "test.sqlite")
    store.save_settings(Settings(model="fake"))
    job = store.create(Brief(name="Alex Rowan", languages=["en"], budget=Budget(pages=1)))["id"]
    engine = Engine(store, SlowAudit, FakeSearch, FakeReader)
    engine.start()
    try:
        store.update(job, status="queued")
        await asyncio.wait_for(started.wait(), 3)
        assert store.job(job)["activity"]["phase"] == "verifying"
        await engine.pause(job)
        assert len(store.detail(job)["candidates"]) == 1
        assert store.detail(job)["conclusion"]["reviewed_claims"] == 0
    finally:
        await engine.close()
    await Engine(store, FakeModel, FakeSearch, FakeReader).run(job)
    detail = store.detail(job)
    assert len(detail["candidates"]) == 1 and detail["conclusion"]["reviewed_claims"] == 1


@pytest.mark.parametrize("grounded,identity", [(False, False), (True, True)])
async def test_ungrounded_or_identity_asserting_observation_is_withheld(tmp_path, grounded, identity):
    class UnsafeObservation(FakeModel):
        async def complete(self, prompt, schema):
            if schema is ObservationReview:
                assert "CITED CLAIMS" in prompt
                return ObservationReview(grounded=grounded, asserts_identity=identity)
            return await super().complete(prompt, schema)

    store = Store(tmp_path / "test.sqlite")
    store.save_settings(Settings(model="fake"))
    job = store.create(Brief(name="Alex Rowan", languages=["en"], budget=Budget(pages=1)))["id"]
    await Engine(store, UnsafeObservation, FakeSearch, FakeReader).run(job)
    detail = store.detail(job)
    assert detail["conclusion"]["reviewed_claims"] == 1
    assert detail["candidates"][0]["assessment"]["note"] == ""
    assert not any(e["level"] == "model" for e in detail["events"])
