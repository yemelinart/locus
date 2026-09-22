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
    "алексей": ["Олексій", "Alexey", "Alexei", "Aleksei", "Aleksey", "Oleksii", "Oleksiy"],
    "олексій": ["Алексей", "Oleksii", "Oleksiy", "Alexey", "Alexei"],
    "сергей": ["Sergey", "Sergei", "Сергій", "Sergii", "Serhii", "Sergiy"],
    "сергій": ["Serhii", "Sergii", "Sergiy", "Сергей", "Sergey"],
    "александр": ["Alexander", "Aleksandr", "Oleksandr", "Олександр"],
    "олександр": ["Oleksandr", "Aleksandr", "Alexander"],
    "юлия": ["Юлія", "Yulia", "Julia", "Yuliya", "Yuliia"],
    "юлія": ["Юлия", "Yuliia", "Yulia", "Julia"],
    "наталья": ["Natalia", "Natalya"],
    "наталія": ["Nataliia", "Natalia"],
    "дмитрий": ["Dmitry", "Dmitri", "Dmytro"],
    "дмитро": ["Dmytro", "Dmitry"],
}


def name_pattern(name):
    """Token-preserving spelling compatibility, never proof of identity."""
    words = name.split()
    exact = r"\s+".join(re.escape(w) for w in words)
    choices = [exact]
    if len(words) == 2:
        first, last = map(re.escape, words)
        choices.append(last + r"(?:,\s*|\s+)" + first)
        if re.fullmatch(r"[А-Яа-яЁёІіЇїЄєҐґ-]+", "".join(words)):
            patronymic = r"[а-яёіїєґ-]+(?:ович|евич|йович|овна|евна|івна|ївна|ична)"
            choices.extend(
                [
                    first + r"\s+" + patronymic + r"\s+" + last,
                    last + r"(?:,\s*|\s+)" + first + r"\s+" + patronymic,
                ]
            )
    return r"(?<!\w)(?:" + "|".join(choices) + r")(?!\w)"


def name_in(text, options, whole=False):
    text = unicodedata.normalize("NFKC", text).strip()
    match = re.fullmatch if whole else re.search
    return any(match(name_pattern(n), text, re.I) for n in options if n.strip())


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
                    # Preserve unchanged surnames (e.g. Стешенко) before speculative spelling changes.
                    add(
                        " ".join([first, *words[1:-1], last]),
                        "hypothesis",
                        "Cross-language given-name hypothesis",
                    )
                    if re.search("[іїєґ]", first, re.I):
                        conservative = last.translate(str.maketrans("иИ", "іІ"))
                        if conservative.startswith("Е"):
                            conservative = "Є" + conservative[1:]
                        add(
                            " ".join([first, *words[1:-1], conservative]),
                            "hypothesis",
                            "Surname spelling hypothesis",
                        )
                    if re.search("[іїєґ]", first, re.I):
                        last = last.translate(str.maketrans("еЕиИёЁыЫэЭ", "єЄіІеЕиИеЕ"))
                    add(
                        " ".join([first, *words[1:-1], last]),
                        "hypothesis",
                        "Cross-language spelling hypothesis",
                    )
        if len(words) >= 2 and all(re.fullmatch(r"[A-Za-z'-]+", word) for word in words):
            for given, spellings in GIVEN.items():
                if words[0].casefold() not in {x.casefold() for x in spellings}:
                    continue
                uk = bool(re.search("[іїєґ]", given))
                chunks = {
                    "shch": "щ",
                    "sch": "щ",
                    "zh": "ж",
                    "kh": "х",
                    "ch": "ч",
                    "sh": "ш",
                    "ts": "ц",
                    "ya": "я",
                    "yu": "ю",
                    "yo": "ё",
                    "ye": "є" if uk else "е",
                    "ie": "є" if uk else "е",
                    "yi": "ї" if uk else "и",
                }
                letters = dict(
                    zip(
                        "abcdefghijklmnopqrstuvwxyz",
                        [
                            "а",
                            "б",
                            "к",
                            "д",
                            "е",
                            "ф",
                            "г",
                            "х",
                            "и",
                            "й",
                            "к",
                            "л",
                            "м",
                            "н",
                            "о",
                            "п",
                            "к",
                            "р",
                            "с",
                            "т",
                            "у",
                            "в",
                            "в",
                            "кс",
                            "й",
                            "з",
                        ],
                    )
                )
                letters.update(
                    {
                        "i": "і" if uk else "и",
                        "y": "и" if uk else "й",
                        "g": "г",
                        "h": "г" if uk else "х",
                        "j": "й",
                        "q": "к",
                        "x": "кс",
                    }
                )

                def cyr(word):
                    return re.sub(
                        "|".join(chunks) + "|[a-z]",
                        lambda m: chunks.get(m[0], letters.get(m[0], m[0])),
                        word.lower(),
                    ).capitalize()

                add(
                    " ".join([given.capitalize(), *[cyr(w) for w in words[1:]]]),
                    "hypothesis",
                    "Reverse transliteration hypothesis",
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
