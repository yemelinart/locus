"""Deterministic analysis and structured exports; no additional model call."""

from collections import Counter
from datetime import datetime, timezone
from html import escape
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

from .localization import translate


def analysis(detail):
    domains = {}
    for source in detail["sources"]:
        domain = urlsplit(source["url"]).hostname or ""
        row = domains.setdefault(
            domain, {"domain": domain, "read": 0, "unavailable": 0, "candidates": 0, "facts": 0}
        )
        row["read" if source["status"] == "read" else "unavailable"] += 1
        matches = [c for c in detail["candidates"] if c["source_id"] == source["id"]]
        row["candidates"] += len(matches)
        row["facts"] += sum(len(c["value"]["facts"]) for c in matches)
    engines = {}
    for run in detail.get("search_runs", []):
        row = engines.setdefault(
            run["engine"],
            {"engine": run["engine"], "attempts": 0, "ok": 0, "failed": 0, "results": 0, "seconds": 0},
        )
        row["attempts"] += 1
        row["ok"] += int(run["status"] == "ok")
        row["failed"] += int(run["status"] == "failed")
        row["results"] += run["result_count"]
        row["seconds"] += run["seconds"]
    reviews = Counter(c["status"] for c in detail["candidates"])
    clues = list(
        dict.fromkeys(
            m for c in detail["candidates"] if c["status"] != "rejected" for m in c["value"]["matches"]
        )
    )
    contradictions = list(
        dict.fromkeys(
            m for c in detail["candidates"] if c["status"] != "rejected" for m in c["value"]["contradictions"]
        )
    )
    return {
        "domains": list(domains.values()),
        "engines": list(engines.values()),
        "facts": sum(len(c["value"]["facts"]) for c in detail["candidates"]),
        "confirmed": reviews["confirmed"],
        "unreviewed": reviews["unreviewed"],
        "rejected": reviews["rejected"],
        "clues": clues,
        "contradictions": contradictions,
        "failed_sources": sum(s["status"] != "read" for s in detail["sources"]),
        "pending_queries": sum(q["state"] == "pending" for q in detail["queries"]),
        "engine_coverage_known": bool(detail.get("search_runs")),
    }


def blocks(detail, lang="en"):
    def t(en, ru):
        return ru if lang == "ru" else en

    a = analysis(detail)
    b = []

    def add(kind, text):
        b.append((kind, str(text)))

    def section(en, ru):
        add("h1", t(en, ru))

    def line(en, ru, value):
        if isinstance(value, str) and len(value) > 18 and value[4:5] == "-" and "T" in value:
            try:
                value = datetime.fromisoformat(value).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            except ValueError:
                pass
        add("p", t(en, ru) + ": " + translate(value, lang))

    add("eyebrow", "LOCUS / RESEARCH REPORT")
    add("title", detail["name"])
    add(
        "p",
        t(
            "Public sources, documented evidence and open questions.",
            "Публичные источники, найденные свидетельства и открытые вопросы.",
        ),
    )
    add(
        "note",
        t(
            "Quote presence is checked against fetched text. Identity and the meaning of each claim still require human review. Source text and earlier findings retain their original language.",
            "Цитаты проверены на присутствие в прочитанном тексте. Личность и смысл каждого утверждения требуют проверки человеком. Текст источников и прежние результаты сохраняют исходный язык.",
        ),
    )
    section("01 / Overview", "01 / Обзор")
    line("Status", "Статус", detail["status"])
    if detail["reason"]:
        line("Stop reason", "Причина остановки", detail["reason"])
    seconds = round(detail["active_seconds"])
    line(
        "Active research time",
        "Активное время поиска",
        f"{seconds // 60:02}:{seconds % 60:02} " + t("(min:sec)", "(мин:сек)"),
    )
    line(
        "Queries / pages read / candidate cards",
        "Запросы / прочитанные страницы / карточки",
        f"{detail['stats']['queries']} / {detail['stats']['sources']} / {len(detail['candidates'])}",
    )
    line(
        "Quoted claims / confirmed / unreviewed / rejected",
        "Утверждения с цитатами / подтверждено / не проверено / отклонено",
        f"{a['facts']} / {a['confirmed']} / {a['unreviewed']} / {a['rejected']}",
    )
    line("Created", "Создано", detail["created_at"])
    line("Report snapshot", "Снимок отчёта", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    section("02 / Starting information", "02 / Исходные сведения")
    brief = detail["brief"]
    budget = brief["budget"]
    for en, ru, key in [
        ("Location", "Место", "city"),
        ("Country", "Страна", "country"),
        ("Context", "Контекст", "context"),
    ]:
        if brief.get(key):
            line(en, ru, brief[key])
    line(
        "Known names",
        "Известные варианты имени",
        ", ".join([brief["name"], *brief.get("aliases", []), *brief.get("previous_names", [])]),
    )
    line("Search languages", "Языки поиска", ", ".join(brief["languages"]))
    line(
        "Budget: minutes / queries / pages / rounds",
        "Бюджет: минуты / запросы / страницы / этапы",
        f"{budget['minutes']} / {budget['queries']} / {budget['pages']} / {budget['rounds']}",
    )
    line("Local model", "Локальная модель", detail["settings_snapshot"].get("model", "—"))
    for en, ru, key in [
        ("Included domains", "Включённые домены", "include_domains"),
        ("Excluded domains", "Исключённые домены", "exclude_domains"),
    ]:
        if brief.get(key):
            line(en, ru, ", ".join(brief[key]))
    section("03 / Search coverage", "03 / Где искали")
    if not a["engines"]:
        add(
            "note",
            t(
                "Per-engine activity was not recorded for this earlier research. Enabled engines are not proof they were queried.",
                "В этом раннем исследовании обращения к отдельным системам не записывались. Включённая система не означает выполненный запрос к ней.",
            ),
        )
    for row in a["engines"]:
        add("h2", row["engine"])
        line(
            "Attempts / results returned / failed attempts",
            "Попытки / результаты выдачи / ошибки",
            f"{row['attempts']} / {row['results']} / {row['failed']}",
        )
    for row in a["domains"]:
        add("h2", row["domain"])
        line(
            "Read / unavailable / quoted claims",
            "Прочитано / недоступно / утверждений с цитатами",
            f"{row['read']} / {row['unavailable']} / {row['facts']}",
        )
    section("04 / Candidate findings", "04 / Возможные совпадения")
    sources = {s["id"]: s for s in detail["sources"]}
    if not detail["candidates"]:
        add(
            "p",
            t(
                "No candidate cards yet. This does not prove that no public information exists.",
                "Карточек пока нет. Это не доказывает отсутствие публичной информации.",
            ),
        )
    for i, candidate in enumerate(detail["candidates"], 1):
        value = candidate["value"]
        source = sources[candidate["source_id"]]
        add("h2", f"{i:02}. {value['name']}")
        line(
            "Review",
            "Проверка",
            {
                "unreviewed": t("Not reviewed", "Не проверено"),
                "confirmed": t("Confirmed by user", "Подтверждено пользователем"),
                "rejected": t("Rejected by user", "Отклонено пользователем"),
            }[candidate["status"]],
        )
        add("p", value["description"])
        for m in value["matches"]:
            add("bullet", t("Matching clue: ", "Совпадающий ориентир: ") + m)
        for m in value["contradictions"]:
            add("warning", t("Contradiction: ", "Противоречие: ") + m)
        for f in value["facts"]:
            add("fact", f["statement"])
            add("quote", f["quote"])
        add("link", source["url"])
        line("Fetched", "Прочитано", source["fetched_at"])
    section("05 / Open questions and next steps", "05 / Открытые вопросы и следующие шаги")
    if a["unreviewed"]:
        add(
            "bullet",
            t(
                "Review candidate cards against known school, work and location clues before combining identities.",
                "Сопоставьте карточки с известными местами учёбы, работы и городами перед объединением людей.",
            ),
        )
    if a["contradictions"]:
        for c in a["contradictions"]:
            add("warning", c)
    if a["failed_sources"]:
        add(
            "bullet",
            t(
                "Some sources were unavailable. Check the source register before treating gaps as absence of information.",
                "Часть источников недоступна. Проверьте список источников перед выводом об отсутствии сведений.",
            ),
        )
    if a["pending_queries"]:
        add(
            "bullet",
            t(
                "Pending queries remain. Increase the relevant budget and resume to process them.",
                "В очереди остались запросы. Увеличьте соответствующий лимит и продолжите поиск.",
            ),
        )
    add(
        "bullet",
        t(
            "Add a known spelling, previous name or public professional reference to narrow the next search.",
            "Добавьте известное написание, прежнее имя или ссылку на публичную профессиональную деятельность для уточнения поиска.",
        ),
    )
    section("06 / Source register", "06 / Реестр источников")
    for i, s in enumerate(detail["sources"], 1):
        add("h2", f"S{i:02} / {s['title'] or urlsplit(s['url']).hostname}")
        add("link", s["url"])
        line("Status", "Статус", s["status"])
        if s["error"]:
            add("warning", translate(s["error"], lang))
    section("07 / Query log", "07 / Поисковые запросы")
    for q in detail["queries"]:
        add("h2", q["payload"]["query"])
        add("p", f"{q['payload']['language'].upper()} / {translate(q['state'], lang)}")
        if q["payload"].get("reason"):
            add("p", q["payload"]["reason"])
        if q["error"]:
            add("warning", translate(q["error"], lang))
    return b


def markdown(detail, lang="en"):
    lines = []
    for kind, text in blocks(detail, lang):
        # Escape user-provided Markdown/HTML; the JSON export retains raw strings.
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        for char in ["\\", "*", "_", "[", "]", "#", "`"]:
            text = text.replace(char, "\\" + char)
        prefix = {
            "title": "# ",
            "h1": "## ",
            "h2": "### ",
            "bullet": "- ",
            "quote": "> ",
            "warning": "! ",
        }.get(kind, "")
        lines += [prefix + text.replace("\n", "\n" + prefix), ""]
    return "\n".join(lines)


def pdf(detail, lang="en"):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate

    assets = Path(__file__).parent / "assets"
    for name, file in [("Locus", "NotoSans-Regular.ttf"), ("LocusBold", "NotoSans-Bold.ttf")]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(assets / file)))
    buffer = BytesIO()
    ink = colors.HexColor("#243a32")
    muted = colors.HexColor("#56645e")
    base = ParagraphStyle(
        "body",
        fontName="Locus",
        fontSize=9.2,
        leading=14,
        textColor=ink,
        spaceAfter=7,
        alignment=TA_LEFT,
        splitLongWords=True,
    )
    styles = {
        "p": base,
        "bullet": ParagraphStyle("bullet", parent=base, leftIndent=12, firstLineIndent=-8),
        "title": ParagraphStyle(
            "title", parent=base, fontName="LocusBold", fontSize=27, leading=34, spaceAfter=16
        ),
        "eyebrow": ParagraphStyle("eyebrow", parent=base, fontSize=8, textColor=muted, spaceAfter=12),
        "h1": ParagraphStyle(
            "section",
            parent=base,
            fontName="LocusBold",
            fontSize=14,
            leading=20,
            spaceBefore=22,
            spaceAfter=11,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "sub",
            parent=base,
            fontName="LocusBold",
            fontSize=10.5,
            leading=16,
            spaceBefore=13,
            keepWithNext=True,
        ),
        "fact": ParagraphStyle("fact", parent=base, fontName="LocusBold", spaceBefore=8, keepWithNext=True),
        "quote": ParagraphStyle(
            "quote",
            parent=base,
            leftIndent=14,
            rightIndent=8,
            textColor=muted,
            borderColor=colors.HexColor("#b1c3b7"),
            borderWidth=0.5,
            borderPadding=8,
            spaceAfter=20,
        ),
        "note": ParagraphStyle(
            "note",
            parent=base,
            textColor=muted,
            backColor=colors.HexColor("#f0f4f0"),
            borderPadding=10,
            spaceBefore=10,
            spaceAfter=16,
        ),
        "warning": ParagraphStyle("warning", parent=base, textColor=colors.HexColor("#834829")),
        "link": ParagraphStyle("link", parent=base, fontSize=8, textColor=muted, spaceBefore=4),
    }
    story = []
    for kind, text in blocks(detail, lang):
        value = escape(text).replace("\n", "<br/>")
        if kind == "bullet":
            value = "• " + value
        if kind == "link" and urlsplit(text).scheme in {"http", "https"}:
            value = f'<link href="{escape(text, quote=True)}">{value}</link>'
        story.append(Paragraph(value, styles.get(kind, base)))

    def frame(canvas, doc):
        canvas.saveState()
        canvas.setFont("Locus", 8)
        canvas.setFillColor(muted)
        canvas.drawString(44, A4[1] - 30, "LOCUS / LOCAL RESEARCH")
        canvas.drawRightString(A4[0] - 44, 24, str(doc.page))
        canvas.drawString(
            44,
            24,
            "Public sources • Human review required"
            if lang == "en"
            else "Публичные источники • Требуется проверка человеком",
        )
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=44,
        leftMargin=44,
        topMargin=55,
        bottomMargin=47,
        title=f"Locus - {detail['name']}",
        author="Locus / Sergey Yemelin",
    )
    doc.build(story, onFirstPage=frame, onLaterPages=frame)
    return buffer.getvalue()
