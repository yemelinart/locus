"""Conservative offline place resolution. A place match is not a person match.

Unknown names/qualifiers and ambiguous homonyms stay unresolved. Never use the
user's desired country to disambiguate a place observed in a source.
"""

import gzip
import json
import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path


def key(text):
    text = "".join(c for c in unicodedata.normalize("NFKD", text).casefold() if not unicodedata.combining(c))
    return " ".join(re.findall(r"[^\W_]+", text.replace("'", "").replace("’", "").replace("ʼ", "")))


def forms(text):
    """Bounded RU/UK case endings, not fuzzy stem matching."""
    value = key(text)
    result = {value}
    if re.fullmatch(r"[а-яёіїєґ]+", value):
        endings = {
            "ская": ("ской", "скую"),
            "ська": ("ській", "ську"),
            "ия": ("ии", "ию"),
            "ія": ("ії", "ію"),
            "жя": ("жі",),
            "ина": ("ине", "ины", "ину"),
            "іна": ("іні", "іни", "іну"),
        }
        for ending, replacements in endings.items():
            if value.endswith(ending):
                result.update(value[: -len(ending)] + r for r in replacements)
                break
    return {key(item) for item in result}


@lru_cache(maxsize=1)
def gazetteer():
    data = json.loads(gzip.decompress((Path(__file__).parent / "geodata/places.json.gz").read_bytes()))
    index = {}
    for row in data["places"]:
        for alias in row[4]:
            if len(key(alias)) >= 3:
                for form in forms(alias):
                    index.setdefault(form, set()).add(row[0])
    return data, {r[0]: r for r in data["places"]}, index


def country_codes(text):
    target = key(text)
    return {
        code
        for code, aliases in gazetteer()[0]["countries"].items()
        if any(target in forms(a) for a in aliases)
    }


def country_equivalent(requested, observed):
    a, b = country_codes(requested), country_codes(observed)
    return bool(a and a == b) or bool(key(requested) and key(requested) == key(observed))


def _qualifier(value):
    words = key(value).split()
    return " ".join(
        w
        for w in words
        if w not in {"region", "oblast", "province", "state", "область", "обл", "області", "области"}
    )


@lru_cache(maxsize=2048)
def resolve(city, country="", region=""):
    data, places, index = gazetteer()
    city_key = key(city)
    # Match the longest place name; the remaining text must be known qualifiers.
    words = city_key.split()
    ids, rest = set(), ""
    for end in range(len(words), 0, -1):
        found = index.get(" ".join(words[:end]))
        if found:
            ids, rest = set(found), " ".join(words[end:])
            break
    codes = country_codes(country) if country.strip() else set()
    if country.strip() and not codes:
        return ()
    if codes:
        ids = {i for i in ids if places[i][2] in codes}
    for qualifier in (rest, region):
        if not qualifier.strip():
            continue
        q = _qualifier(qualifier)
        ids = {
            i
            for i in ids
            if q
            and q
            in {
                *(f for a in data["admins"].get(places[i][3], []) for f in forms(_qualifier(a))),
                *(f for a in data["countries"].get(places[i][2], []) for f in forms(_qualifier(a))),
            }
        }
    return tuple(sorted(ids))


def city_equivalent(requested, country, observed, observed_country="", observed_region=""):
    wanted = resolve(requested, country)
    found = resolve(observed, observed_country, observed_region)
    if wanted or found:
        return len(wanted) == len(found) == 1 and wanted == found
    # Unlisted small places still work with exact names, but never discard a qualifier.
    return bool(key(requested) and key(requested) == key(observed)) and (
        not observed_country or not country or country_equivalent(country, observed_country)
    )


def search_spellings(city, country="", limit=8):
    result = [city.strip()] if city.strip() else []
    ids = resolve(city, country)
    if len(ids) != 1:
        return result
    row = gazetteer()[1][ids[0]]
    # Prefer a canonical Latin name, then RU/UK aliases, then other Latin spellings.
    latin = [a for a in row[4] if re.fullmatch(r"[A-Za-zÀ-ž '’ʼ-]+", a)]
    latin.sort(key=lambda a: SequenceMatcher(None, key(row[1]), key(a)).ratio(), reverse=True)
    cyrillic = [a for a in row[4] if re.fullmatch(r"[А-Яа-яЁёІіЇїЄєҐґ '’ʼ-]+", a)]
    cyrillic.sort(
        key=lambda a: (bool(re.search("[іїєґ]", a, re.I)), SequenceMatcher(None, key(city), key(a)).ratio()),
        reverse=True,
    )
    choices = [row[1], *cyrillic[:3], *latin, *row[4]]
    for alias in choices:
        if not re.fullmatch(r"[A-Za-zÀ-žА-Яа-яЁёІіЇїЄєҐґ '’ʼ-]+", alias) or len(alias) < 4:
            continue
        if key(alias) not in {key(v) for v in result}:
            result.append(alias)
        if len(result) >= limit:
            break
    return result


def prompt_context(brief):
    ids = resolve(brief.city, brief.country) if brief.city else ()
    rows = [gazetteer()[1][i] for i in ids[:4]]
    return {
        "requested_city_resolution": "resolved" if len(ids) == 1 else "ambiguous_or_unlisted",
        "places": [
            {
                "id": r[0],
                "city": r[1],
                "country_code": r[2],
                "region": gazetteer()[0]["admins"].get(r[3], [])[:5],
            }
            for r in rows
        ],
        "spelling_hypotheses": search_spellings(brief.city, brief.country),
    }
