from types import SimpleNamespace

import pytest
from ddgs.exceptions import DDGSException, RatelimitException
from locus.discovery import contextual, portfolio, seed_queries
from locus.identity import IdentityCheck, validate_checks
from locus.models import Brief, Query
from locus.names import name_in
from locus.places import city_equivalent, country_equivalent, resolve, search_spellings
from locus.providers.search_worker import search_request
from locus.verification import CandidateAudit, excerpt_for, validate_audit


@pytest.mark.asyncio
async def test_optional_narrative_timeout_cannot_erase_identity_review(tmp_path):
    from locus.db import Store
    from locus.engine import Engine
    from locus.models import Budget, Extraction, Settings
    from locus.verification import ObservationReview

    quote = "Alex Rowan works as a designer in Dolynska, Ukraine."

    class Reader:
        def __init__(self, *args):
            pass

        async def read(self, url, *args):
            return {"url": url, "title": "Professional profile", "body": quote, "content_hash": "fixture"}

    class Search:
        def __init__(self, *args):
            self.last_audit = []

    class Model:
        def __init__(self, *args):
            pass

        async def complete(self, prompt, schema):
            if schema is Extraction:
                return Extraction(
                    candidates=[
                        {
                            "name": "Alex Rowan",
                            "facts": [{"category": "public_profile", "statement": quote, "quote": quote}],
                        }
                    ]
                )
            if schema is ObservationReview:
                raise TimeoutError("Optional observation timed out")
            return CandidateAudit(
                name_relation="same_spelling",
                name_quote=quote,
                claims=[{"index": 0, "verdict": "supported"}],
                identity_checks=[
                    IdentityCheck(
                        field="city",
                        observed="Dolynska",
                        quote=quote,
                        relation="supports",
                        same_place=True,
                        same_subject=True,
                    )
                ],
                note="Alex Rowan works as a designer.",
                note_facts=[0],
            )

    s = Store(tmp_path / "db.sqlite")
    s.save_settings(Settings(model="fixture"))
    j = s.create(
        Brief(
            name="Alex Rowan",
            city="Dolynska",
            seed_urls=["https://example.org/alex"],
            budget=Budget(minutes=1, pages=1, queries=1, rounds=1),
        )
    )["id"]
    await Engine(s, Model, Search, Reader).run(j)
    d = s.detail(j)
    candidate = d["candidates"][0]["assessment"]
    assert candidate["model_reviewed"] and candidate["identity_status"] == "eligible"
    assert candidate["note"] == "" and len(candidate["checked_facts"]) == 1
    assert d["conclusion"]["state"] == "possible"


def test_place_aliases_and_region_qualifiers_resolve_offline():
    assert resolve("Запорожье", "Украина") == resolve("Запоріжжя", "Ukraine") == resolve("Zaporizhzhia", "UA")
    assert resolve("Александрия Кировоградская область", "Украина") == ("698625",)
    assert resolve("Alexandria, Kirovohrad region", "Ukraine") == ("698625",)
    assert resolve("Александрия Орловская область", "Украина") == ()
    assert city_equivalent("Долинская", "Украина", "Dolynska")
    assert country_equivalent("Україна", "Ukraine")
    assert city_equivalent("Запорожье", "Украина", "Запоріжжі", "Україні")
    assert city_equivalent("Долинская", "Украина", "Долинській", "Україні")
    assert city_equivalent(
        "Александрия Кировоградская область", "Украина", "Александрии", "Украине", "Кировоградской области"
    )


@pytest.mark.parametrize(
    "observed,country",
    [
        ("Moscow", "Russia"),
        ("Alexandria", "Egypt"),
        ("Alexandria", ""),
        ("New York", "US"),
    ],
)
def test_desired_country_never_disambiguates_observed_city(observed, country):
    assert not city_equivalent("Александрия", "Украина", observed, country)


def test_wrong_place_cannot_pass_even_when_model_claims_same_place():
    b = Brief(name="Alex Rowan", city="Запорожье", country="Украина")
    body = "Alex Rowan works as a designer in Moscow, Russia."
    checks = [
        IdentityCheck(
            field=k, observed=v, relation="supports", same_place=True, same_subject=True, quote=body
        )
        for k, v in [("city", "Moscow"), ("country", "Russia")]
    ]
    assert all(c["relation"] == "unknown" for c in validate_checks(checks, b, b.name, body, body))


def test_fabricated_region_cannot_resolve_a_quoted_homonym():
    b = Brief(name="Alex Rowan", city="Alexandria", country="Ukraine")
    body = "Alex Rowan studied design in Alexandria."
    raw = IdentityCheck(
        field="city",
        observed="Alexandria",
        observed_country="Ukraine",
        relation="supports",
        same_place=True,
        same_subject=True,
        quote=body,
    )
    assert validate_checks([raw], b, b.name, body, body)[0]["relation"] == "unknown"


@pytest.mark.parametrize(
    "name",
    [
        "Алексей Иванов",
        "Иванов Алексей",
        "Иванов, Алексей",
        "Алексей Петрович Иванов",
        "Иванов Алексей Петрович",
    ],
)
def test_name_order_and_patronymic_preserve_the_person_tokens(name):
    assert name_in(name, ["Алексей Иванов"], whole=True)


@pytest.mark.parametrize(
    "name",
    [
        "Алексей Запорожье",
        "Иван Иванов",
        "Алексей и Пётр Иванов",
        "Алексей Москва Иванов",
        "Алексей Ивановский",
    ],
)
def test_city_or_other_subject_cannot_replace_part_of_name(name):
    assert not name_in(name, ["Алексей Иванов"], whole=True)


def test_quote_naming_two_people_does_not_validate_the_wrong_candidate():
    b = Brief(name="Алексей Иванов", city="Запорожье")
    body = "Алексей Иванов работает вместе с дизайнером Алексей Запорожье."
    value = {"name": "Алексей Запорожье", "facts": []}
    raw = CandidateAudit(name_relation="same_spelling", name_quote=body)
    assert validate_audit(raw, value, b, body, body)["name_relation"] == "different"


def test_excerpt_finds_patronymic_at_page_tail():
    body = ("Unrelated paragraph. " * 900) + "Алексей Петрович Иванов учился в Запорожье."
    excerpt = excerpt_for(body, Brief(name="Алексей Иванов"), 3000)
    assert "Алексей Петрович Иванов" in excerpt


def test_query_quotes_and_bounded_exploration():
    b = Brief(name="Алексей Иванов", city="Запорожье", country="Ukraine")
    q = Query(query='\\"Алексей Иванов\\" \\"Запорожье\\"', language="ru")
    assert q.query == '"Алексей Иванов" "Запорожье"'
    planned = [Query(query=f'"Алексей Иванов" random{i}', language="ru") for i in range(10)]
    choices = portfolio(b, planned, [], 12, first_round=True)
    assert sum(not contextual(q, b) for q in choices) <= 2
    assert any("Запоріжжя" in q.query for q in seed_queries(b))
    assert "Zaporizhzhia" in search_spellings(b.city, b.country)


def test_empty_adapter_result_does_not_become_outage(monkeypatch):
    def empty(*args, **kwargs):
        raise DDGSException("No results found.")

    monkeypatch.setattr("locus.providers.search_worker.DDGS", lambda **kw: SimpleNamespace(text=empty))
    result = search_request({"query": "fictional", "backend": "duckduckgo", "timeout": 5})
    assert result["results"] == [] and "not verified" in result["notice"]


@pytest.mark.parametrize("exc", [DDGSException("HTTP 403"), RatelimitException("No results found.")])
def test_actual_adapter_errors_remain_errors(monkeypatch, exc):
    def failure(*args, **kwargs):
        raise exc

    monkeypatch.setattr("locus.providers.search_worker.DDGS", lambda **kw: SimpleNamespace(text=failure))
    with pytest.raises(type(exc)):
        search_request({"query": "fictional", "backend": "duckduckgo", "timeout": 5})
