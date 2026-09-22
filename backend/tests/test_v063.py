import pytest
from locus.db import Store, dump, now, uid
from locus.engine import Engine
from locus.evidence import assessment_label
from locus.models import Brief, Budget, Extraction, Finding, Plan, Settings
from locus.navigation import planned_trails, source_identity
from locus.verification import CandidateAudit, validate_audit
from test_v06 import linked_fixture

NAME = "Alex Rowan"
UNKNOWN = "Alex Rowan wrote Example Book."
KNOWN = "Alex Rowan works in Dolynska."


def links():
    return [
        {"url": "https://example.org/book", "context": "Alex Rowan wrote Example Book", "kind": "hyperlink"},
        {
            "url": "https://example.org/works",
            "context": "Alex Rowan → publications",
            "kind": "profile_navigation",
            "person": NAME,
        },
        {
            "url": "https://example.org/bio",
            "context": "Alex Rowan → Biography",
            "kind": "profile_navigation",
            "person": NAME,
        },
        {
            "url": "https://other.example.org/profile",
            "context": NAME,
            "kind": "declared_same_as",
            "person": NAME,
        },
    ]


def audit_for(body):
    return CandidateAudit(
        name_relation="same_spelling",
        name_quote=body,
        claims=[{"index": 0, "verdict": "supported"}],
        identity_checks=[
            {
                "field": "city",
                "observed": "Dolynska",
                "relation": "supports",
                "quote": body,
                "same_subject": True,
                "same_place": True,
            }
        ]
        if "Dolynska" in body
        else [],
    )


def saved(s, body=UNKNOWN):
    brief = Brief(name=NAME, city="Dolynska", languages=["en"], budget=Budget(queries=1, pages=5, rounds=1))
    j = s.create(brief)["id"]
    sid, cid = uid(), uid()
    value = Finding(
        name=NAME, facts=[{"category": "public_profile", "statement": body, "quote": body}]
    ).model_dump()
    with s.connect() as c:
        c.execute(
            "INSERT INTO sources(id,job_id,url,title,body,status,fetched_at,links) VALUES(?,?,?,?,?,'read',?,?)",
            (sid, j, "https://example.org/", "Profile", body, now(), dump(links())),
        )
        c.execute(
            "INSERT INTO candidates(id,job_id,source_id,value) VALUES(?,?,?,?)", (cid, j, sid, dump(value))
        )
    s.save_audit(cid, 1, validate_audit(audit_for(body), value, brief, body, body), "fixture")
    return j, sid, cid, brief


def test_name_only_assessment_never_claims_positive_match_in_export(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    j, sid, cid, brief = saved(s)
    d = s.detail(j)
    a = d["candidates"][0]["assessment"]
    assert d["conclusion"]["state"] == "no_supported_findings"
    assert a["identity_status"] == "unresolved"
    assert assessment_label(a) == "Name only · identity unconfirmed"
    assert assessment_label(a, "ru") == "Только имя · личность не установлена"
    from locus.reports import markdown

    assert "Name only · identity unconfirmed" in markdown(d)


def test_unconfirmed_namesake_can_only_follow_bio_or_declared_profile(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    j, sid, cid, brief = saved(s)
    d = s.detail(j)
    assert source_identity(d, sid) == "unresolved"
    selected = planned_trails(d, d["sources"][0], brief)
    assert [x["url"] for x in selected] == ["https://example.org/bio", "https://other.example.org/profile"]
    # A manual name-based confirmation alone cannot remove the required city gate.
    with s.connect() as c:
        c.execute("UPDATE candidates SET status='confirmed' WHERE id=?", (cid,))
    assert source_identity(s.detail(j), sid) == "unresolved"
    # Domain exclusions and explicit rejections still control navigation.
    brief.exclude_domains = ["other.example.org"]
    assert len(planned_trails(d, d["sources"][0], brief)) == 1
    with s.connect() as c:
        c.execute("UPDATE candidates SET status='rejected' WHERE id=?", (cid,))
    d = s.detail(j)
    assert not planned_trails(d, d["sources"][0], brief)


def test_verified_source_can_expand_public_work_and_confirmed_groups_can_supply_criteria(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    j, sid, cid, brief = saved(s, KNOWN)
    d = s.detail(j)
    assert source_identity(d, sid) == "eligible"
    assert len(planned_trails(d, d["sources"][0], brief)) == 4
    other, ids, _ = linked_fixture(s)
    grouped = s.review_link(other, *ids, "confirmed")
    assert all(source_identity(grouped, c["source_id"]) == "eligible" for c in grouped["candidates"])


@pytest.mark.parametrize("known", [False, True])
async def test_model_identity_verdict_controls_actual_crawl_not_just_ui(tmp_path, known):
    s = Store(tmp_path / "db.sqlite")
    s.save_settings(Settings(model="fixture"))
    brief = Brief(
        name=NAME,
        city="Dolynska",
        languages=["en"],
        seed_urls=["https://example.org/"],
        budget=Budget(queries=1, pages=5, rounds=1),
    )
    j = s.create(brief)["id"]
    operations = []

    class Reader:
        def __init__(self, *args):
            pass

        async def read(self, url, *args):
            operations.append(("read", url))
            body = KNOWN if known or url.endswith("/bio") else UNKNOWN
            return {
                "url": url,
                "title": "Profile",
                "body": body,
                "content_hash": url,
                "links": links() if url.endswith(".org/") else [],
            }

    class Search:
        def __init__(self, *args):
            pass

        async def search(self, *args):
            return []

    class Model:
        def __init__(self, *args):
            pass

        async def complete(self, prompt, schema):
            if schema is Plan:
                return Plan(queries=[])
            body = KNOWN if KNOWN in prompt else UNKNOWN
            if schema is CandidateAudit:
                operations.append(("audit", body))
                return audit_for(body)
            assert schema is Extraction
            return Extraction(
                candidates=[
                    {
                        "name": NAME,
                        "facts": [{"category": "public_profile", "statement": body, "quote": body}],
                    }
                ]
            )

    await Engine(s, Model, Search, Reader).run(j)
    reads = [value for kind, value in operations if kind == "read"]
    assert "https://example.org/bio" in reads
    assert ("https://example.org/book" in reads) == known
    assert ("https://example.org/works" in reads) == known
    # No automatic page expansion occurs before the model reviews the source.
    assert operations[1][0] == "audit"
    assert s.detail(j)["status"] == "completed"


async def test_legacy_unconfirmed_book_queue_is_deferred_without_spending_page_budget(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    s.save_settings(Settings(model="fixture"))
    j, sid, cid, brief = saved(s)
    with s.connect() as c:
        c.execute("UPDATE sources SET links=? WHERE id=?", (dump(links()[:2]), sid))
    s.enqueue(
        j,
        "fetch",
        "https://example.org/book",
        {"url": "https://example.org/book", "from_source": sid, "depth": 1, "priority": 10},
    )

    class Reader:
        def __init__(self, *args):
            pass

        async def read(self, *args):
            raise AssertionError("Must not read this namesake book")

    class Search:
        def __init__(self, *args):
            pass

        async def search(self, *args):
            return []

    class Model:
        def __init__(self, *args):
            pass

        async def complete(self, prompt, schema):
            assert schema is Plan
            return Plan(queries=[])

    await Engine(s, Model, Search, Reader).run(j)
    assert s.job(j)["stats"]["pages"] == 0
    with s.connect() as c:
        row = c.execute("SELECT state,error FROM tasks WHERE kind='fetch'").fetchone()
    assert row["state"] == "superseded" and "identity criteria" in row["error"]
    # It remains recoverable if later evidence legitimately establishes the link.
    value = s.detail(j)["candidates"][0]["value"]
    value["facts"] = [{"category": "public_profile", "statement": KNOWN, "quote": KNOWN}]
    with s.connect() as c:
        c.execute("UPDATE candidates SET value=? WHERE id=?", (dump(value), cid))
        c.execute("UPDATE sources SET body=? WHERE id=?", (KNOWN, sid))
    s.save_audit(cid, 1, validate_audit(audit_for(KNOWN), value, brief, KNOWN, KNOWN), "fixture")
    Engine(s).expand_source(j, sid, brief)
    assert s.task(j, "fetch")["key"] == "https://example.org/book"


def test_resume_retains_depth_limit_through_source_redirect_alias(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    j, sid, cid, brief = saved(s, KNOWN)
    alias = "https://example.org/redirect"
    with s.connect() as c:
        c.execute("UPDATE sources SET url_aliases=? WHERE id=?", (dump([alias]), sid))
    s.enqueue(j, "fetch", alias, {"url": alias, "depth": 2})
    task = s.task(j, "fetch")
    s.finish_task(task["id"])
    Engine(s).expand_source(j, sid, brief)
    assert s.task(j, "fetch") is None
    # A genuinely independent search arrival at depth zero allows expansion.
    s.enqueue(j, "fetch", "https://example.org/", {"url": "https://example.org/"})
    task = s.task(j, "fetch")
    s.finish_task(task["id"])
    Engine(s).expand_source(j, sid, brief)
    assert s.task(j, "fetch") is not None
