"""Bounded spelling hypotheses, never identity evidence or invented married surnames."""

import re
import unicodedata

from .models import Brief

RUS = dict(
    zip(
        "абвгдеёжзийклмнопрстуфхцчшщыэюяьъ",
        [
            "a",
            "b",
            "v",
            "g",
            "d",
            "e",
            "yo",
            "zh",
            "z",
            "i",
            "y",
            "k",
            "l",
            "m",
            "n",
            "o",
            "p",
            "r",
            "s",
            "t",
            "u",
            "f",
            "kh",
            "ts",
            "ch",
            "sh",
            "shch",
            "y",
            "e",
            "yu",
            "ya",
            "",
            "",
        ],
    )
)
UKR = RUS | {"г": "h", "ґ": "g", "и": "y", "і": "i", "ї": "yi", "є": "ye"}
GIVEN = {
    "сергей": ["Sergey", "Sergei", "Сергій", "Sergii", "Serhii", "Sergiy"],
    "сергій": ["Serhii", "Sergii", "Sergiy", "Сергей", "Sergey"],
    "александр": ["Alexander", "Aleksandr", "Oleksandr", "Олександр"],
    "олександр": ["Oleksandr", "Aleksandr", "Alexander"],
    "юлия": ["Yulia", "Julia", "Yuliya"],
    "юлія": ["Yuliia", "Yulia", "Julia"],
    "наталья": ["Natalia", "Natalya"],
    "наталія": ["Nataliia", "Natalia"],
    "дмитрий": ["Dmitry", "Dmitri", "Dmytro"],
    "дмитро": ["Dmytro", "Dmitry"],
}


def variants(brief: Brief) -> list[dict]:
    result = []
    seen = set()

    def add(value, origin, reason):
        value = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()
        if value.casefold() not in seen and value and (origin == "supplied" or len(result) < 24):
            seen.add(value.casefold())
            result.append({"name": value, "origin": origin, "reason": reason})

    add(brief.name, "supplied", "Original name")
    for value in brief.aliases + brief.previous_names:
        add(value, "supplied", "User-provided spelling or previous name")
    if not brief.expand_names:
        return result
    for value in [brief.name, *brief.aliases, *brief.previous_names]:
        words = value.split()
        if len(words) >= 2:
            for first in GIVEN.get(words[0].casefold(), []):
                if re.search("[а-яіїєґ]", first, re.I):
                    last = words[-1]
                    if re.search("[іїєґ]", first, re.I):
                        last = last.translate(str.maketrans("еЕиИёЁыЫэЭ", "єЄіІеЕиИеЕ"))
                    add(
                        " ".join([first, *words[1:-1], last]),
                        "hypothesis",
                        "Cross-language spelling hypothesis",
                    )
        for mapping in [RUS, UKR]:
            words = value.split()
            roman = ["".join(mapping.get(c, c) for c in w.lower()).capitalize() for w in words]
            if re.search("[а-яёіїєґ]", value, re.I):
                add(" ".join(roman), "hypothesis", "Transliteration hypothesis")
                if len(words) >= 2:
                    surname = roman[-1]
                    surnames = [surname]
                    if surname.startswith("E"):
                        surnames += ["Ye" + surname[1:], "Ie" + surname[1:]]
                    if re.search("[еє]", words[-1], re.I):
                        ie = "".join(
                            ("ie" if c in "еє" else mapping.get(c, c)) for c in words[-1].lower()
                        ).capitalize()
                        surnames.append(ie)
                    for first in GIVEN.get(words[0].casefold(), [roman[0]]):
                        for last in surnames:
                            # Do not mix alphabets in one hypothesis.
                            if not re.search("[а-яіїєґ]", first, re.I):
                                add(
                                    " ".join([first, *roman[1:-1], last]),
                                    "hypothesis",
                                    "Name and transliteration hypothesis",
                                )
            # ASCII diacritics variant is useful for already Latin names.
        plain = "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))
        add(plain, "hypothesis", "Diacritic-free spelling")
    return result
