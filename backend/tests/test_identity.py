import pytest
from locus.db import Store, dump, now, uid
from locus.evidence import assess
from locus.identity import IdentityCheck, discovery_priority, resolution, validate_checks
from locus.models import Brief, Settings
from locus.providers.search import target_region
from locus.reports import markdown
from locus.verification import AUDIT_METHOD


def brief():
    return Brief(name="Alex Rowan", city="Dolynska", country="Ukraine", year_from=1980, year_to=1984)


def checks(body, year=1982):
    return [
        IdentityCheck(
            field=k,
            relation="supports",
            quote=body,
            observed=v,
            same_subject=True,
            same_place=True,
            birth_year=year if k == "birth_year" else None,
        )
        for k, v in [("city", "Dolynska"), ("country", "Ukraine"), ("birth_year", str(year))]
    ]


def test_all_required_criteria_need_grounded_support():
    b = brief()
    body = "Alex Rowan is a designer from Dolynska, Ukraine, born in 1982."
    result = validate_checks(checks(body), b, b.name, body, body)
    assert resolution(result, True) == "eligible"
    assert resolution(result, False) == "unresolved"
    assert resolution(validate_checks(checks(body)[:1], b, b.name, body, body), True) == "unresolved"
    assert resolution(validate_checks([], b, b.name, body, body), True) == "unresolved"


@pytest.mark.parametrize("mode", ["fabricated", "other_subject", "duplicate", "wrong_place", "missing_name"])
def test_invalid_geographic_evidence_fails_closed(mode):
    b = brief()
    body = "Alex Rowan is a designer from Dolynska, Ukraine, born in 1982."
    review = checks(body)
    if mode == "fabricated":
        review[0].quote += " Invented."
    if mode == "other_subject":
        review[0].same_subject = False
    if mode == "duplicate":
        review.append(review[0])
    if mode == "wrong_place":
        review[0].same_place = False
    if mode == "missing_name":
        review[0].quote = "A designer from Dolynska, Ukraine, born in 1982."
    assert resolution(validate_checks(review, b, b.name, body, body), True) == "unresolved"


def test_year_range_is_arithmetic_and_publication_year_is_not_birth():
    b = brief()
    body = "Alex Rowan is a designer from Dolynska, Ukraine, born in 1999."
    result = validate_checks(checks(body, 1999), b, b.name, body, body)
    assert result[-1]["relation"] == "contradicts"
    body = body.replace("born in", "published work in")
    result = validate_checks(checks(body, 1999), b, b.name, body, body)
    assert result[-1]["relation"] == "unknown"
    body = "Alex Rowan is a designer from Dolynska, Ukraine, not born in 1982."
    assert validate_checks(checks(body), b, b.name, body, body)[-1]["relation"] == "unknown"


def test_geographic_reading_priority_and_region_are_not_identity_evidence(tmp_path):
    b = brief()
    exact = {"title": "Alex Rowan", "snippet": "Designer from Dolynska, Ukraine"}
    vague = {"title": "Alex Rowan", "snippet": "Designer"}
    assert discovery_priority(exact, b) > discovery_priority(vague, b)
    s = Store(tmp_path / "db.sqlite")
    j = s.create(b)["id"]
    s.enqueue(j, "fetch", "first", {"priority": discovery_priority(vague, b)})
    s.enqueue(j, "fetch", "second", {"priority": discovery_priority(exact, b)})
    assert s.task(j, "fetch")["key"] == "second"
    assert s.detail(j)["conclusion"]["reviewed_claims"] == 0
    assert target_region(Settings(), b, "en") == "ua-uk"
    assert target_region(Settings(search_region="de-de"), b, "en") == "de-de"


def test_another_city_is_not_an_explicit_denial_of_past_connection():
    b = brief()
    body = "Alex Rowan is a designer from Oryol, Russia, born in 1982."
    raw = [
        IdentityCheck(field="city", relation="contradicts", quote=body, observed="Oryol", same_subject=True),
        IdentityCheck(
            field="country", relation="contradicts", quote=body, observed="Russia", same_subject=True
        ),
    ]
    assert resolution(validate_checks(raw, b, b.name, body, body), True) == "unresolved"


def test_old_high_score_does_not_override_unknown_criteria(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    b = brief()
    j = s.create(b)["id"]
    sid, cid = uid(), uid()
    body = "Alex Rowan is a designer from Orlov, Russia, born in 1982."
    value = {
        "name": b.name,
        "matches": [],
        "contradictions": [],
        "description": "",
        "facts": [{"statement": "Designer in Orlov", "quote": body, "category": "professional_role"}],
    }
    with s.connect() as c:
        c.execute(
            "INSERT INTO sources(id,job_id,url,title,body,status,fetched_at) VALUES(?,?,?,?,?,'read',?)",
            (sid, j, "https://example.org/person", "Public profile", body, now()),
        )
        c.execute(
            "INSERT INTO candidates(id,job_id,source_id,value) VALUES(?,?,?,?)", (cid, j, sid, dump(value))
        )
    audit = {
        "method": AUDIT_METHOD,
        "status": "reviewed",
        "accepted_facts": [0],
        "name_quote": body,
        "name_relation": "same_spelling",
        "supported": [
            {"index": 0, "kind": "education", "text": "School", "quote": body},
            {"index": 1, "kind": "organization", "text": "Studio", "quote": body},
        ],
        "conflicts": [],
    }
    s.save_audit(cid, 1, audit, "fixture")
    d = s.detail(j)
    assert d["candidates"][0]["assessment"]["identity_status"] == "unresolved"
    assert d["candidates"][0]["assessment"]["level"] == "limited"
    assert d["conclusion"]["promising_ids"] == [] and d["conclusion"]["reviewed_claims"] == 0
    assert "Designer in Orlov" not in markdown(d)
    assert "Not included among matching profiles" in markdown(d)
    # Even a prior manual confirmation does not silently erase required filters.
    with s.connect() as c:
        c.execute("UPDATE candidates SET status='confirmed' WHERE id=?", (cid,))
    assert "Your confirmed profile —" not in markdown(s.detail(j))


def test_criteria_change_invalidates_prior_matching_place():
    b = brief()
    body = "Alex Rowan is a designer from Dolynska, Ukraine, born in 1982."
    audit = {
        "method": AUDIT_METHOD,
        "status": "reviewed",
        "revision": 1,
        "name_quote": body,
        "accepted_facts": [],
        "name_relation": "same_spelling",
        "identity_checks": validate_checks(checks(body), b, b.name, body, body),
    }
    c = {"value": {"name": b.name, "facts": []}, "status": "unreviewed", "verification": audit}
    assert assess(c, {}, b.model_dump(), 1)["identity_status"] == "eligible"
    b.city = "Other town"
    assert assess(c, {}, b.model_dump(), 2)["identity_status"] == "unresolved"
