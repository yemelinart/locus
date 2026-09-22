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
    if detail.get("conclusion"):
        from .evidence import CONCLUSIONS

        summary = detail["conclusion"]
        section("Research conclusion", "Вывод исследования")
        if detail.get("retryable_model_steps"):
            line(
                "AI steps awaiting retry",
                "Шагов ИИ в ожидании повторной проверки",
                str(detail["retryable_model_steps"]),
            )
        add("h2", CONCLUSIONS[summary["state"]][lang == "ru"])
        add(
            "p",
            t(
                "Supported claims / cards awaiting semantic review / source access failures",
                "Утверждения после проверки / карточки в ожидании проверки / недоступные источники",
            )
            + f": {summary['reviewed_claims']} / {summary['pending_cards']} / {summary['unavailable_sources']}",
        )
        add(
            "note",
            t(
                "This is a partial snapshot of the checked sources, not a complete biography or a probability of identity. No result does not prove that no information exists.",
                "Это частичный результат проверки источников, а не полная биография или вероятность личности. Отсутствие результата не доказывает отсутствие информации.",
            ),
        )
        if summary["provisional"]:
            add(
                "p",
                t(
                    "Research has unfinished work; this conclusion is provisional.",
                    "Не вся работа завершена; вывод предварительный.",
                ),
            )
        line(
            "Connections still unverified",
            "Связь с критериями не подтверждена",
            str(summary.get("unresolved_identity", 0)),
        )
        line(
            "Conflicting with required criteria",
            "Противоречат обязательным критериям",
            str(summary.get("conflicting_identity", 0)),
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
    linked_groups = detail.get("linkage", {}).get("groups", [])
    if linked_groups:
        section("Evidence across linked sources", "Свидетельства из связанных источников")
        add(
            "note",
            t(
                "Links were confirmed by the user. Original records remain separate. A shared name or a hyperlink alone does not establish identity. Source families are a conservative grouping, not proof of independent corroboration.",
                "Связи подтверждены пользователем. Исходные записи сохранены отдельно. Совпадение имени или ссылка сами по себе не устанавливают личность. Группы источников не доказывают независимое подтверждение.",
            ),
        )
        source_map = {s["id"]: s for s in detail["sources"]}
        candidate_map = {c["id"]: c for c in detail["candidates"]}
        states = {
            "eligible": t("Required criteria supported", "Обязательные критерии подтверждены"),
            "unresolved": t("Required criteria remain unknown", "Критерии не подтверждены"),
            "conflicting": t("Conflicting evidence", "Противоречивые сведения"),
            "no_constraints": t("No matching criteria supplied", "Критерии не заданы"),
        }
        for group in linked_groups:
            add(
                "h2",
                candidate_map[group["candidate_ids"][0]]["value"]["name"]
                + " · "
                + states[group["identity_status"]],
            )
            line(
                "Sources / source families",
                "Источники / группы источников",
                f"{group['source_count']} / {group['source_families']}",
            )
            for check in group["identity_checks"]:
                add(
                    "p",
                    check["requested"]
                    + ": "
                    + {
                        "supports": t("supported", "подтверждено"),
                        "contradicts": t("contradiction", "противоречие"),
                        "unknown": t("unknown", "неизвестно"),
                    }[check["relation"]],
                )
                for evidence in check["evidence"]:
                    add("quote", evidence["quote"])
                    add("link", source_map[evidence["source_id"]]["url"])
            if group["identity_status"] == "eligible":
                for cid in group["candidate_ids"]:
                    member = candidate_map[cid]
                    for fact in member["assessment"]["checked_facts"]:
                        add("fact", fact["statement"])
                        add("quote", fact["quote"])
                        add("link", source_map[member["source_id"]]["url"])
    confirmed_profile = [
        c
        for c in detail["candidates"]
        if c["status"] == "confirmed"
        and not c.get("assessment", {}).get("excluded")
        and not c.get("assessment", {}).get("review_outdated")
        and c.get("assessment", {}).get("identity_status") not in {"unresolved", "conflicting"}
        and c.get("assessment", {}).get("checked_facts")
    ]
    if confirmed_profile:
        section(
            "Your confirmed profile — public work and education",
            "Подтверждённый вами профиль — публичная деятельность и образование",
        )
        add(
            "note",
            t(
                "This overview combines only cards you confirmed under the current criteria. Quotations and original links remain attached. It is not a complete life history.",
                "Обзор объединяет только карточки, подтверждённые вами при текущих критериях. Цитаты и исходные ссылки сохранены. Это не полная история жизни.",
            ),
        )
        source_map = {s["id"]: s for s in detail["sources"]}
        for candidate in confirmed_profile:
            source = source_map[candidate["source_id"]]
            for f in candidate["assessment"]["checked_facts"]:
                add("fact", f["statement"])
                add("quote", f["quote"])
                add("link", source["url"])
    if detail.get("leads"):
        section("Discovered links · identity unverified", "Найденные ссылки · личность не установлена")
        add(
            "p",
            t(
                "Search previews and page titles are leads, not verified biographical facts. Blocked pages can be opened manually.",
                "Заголовки и текст поисковой выдачи — зацепки, а не проверенные факты биографии. Недоступные для автоматического чтения страницы можно открыть вручную.",
            ),
        )
        for lead in detail["leads"]:
            add("h2", lead["title"])
            add("link", lead["url"])
            line("Page status", "Статус страницы", lead["state"])
            if lead["query"]:
                line("Discovery query", "Поисковый запрос", lead["query"])

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
    for clue in brief.get("evidence_clues", []):
        line("Comparison clue", "Ориентир для сравнения", clue["kind"] + ": " + clue["text"])
    if detail.get("revisions"):
        line("Criteria revision", "Версия критериев", str(detail.get("revision", 1)))
        for revision in detail["revisions"]:
            stamp = datetime.fromisoformat(revision["at"]).strftime("%Y-%m-%d %H:%M UTC")
            add(
                "bullet",
                f"v{revision['number']} · {stamp}"
                + (" · " + revision["brief"]["context"] if revision["brief"]["context"] else ""),
            )
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
        assessment = candidate.get("assessment")
        if assessment:
            from .evidence import assessment_label

            line("Identity assessment", "Оценка личности", assessment_label(assessment, lang))
        if assessment and assessment.get("identity_checks"):
            for criterion in assessment["identity_checks"]:
                label = {
                    "supports": t("Supported", "Подтверждено"),
                    "contradicts": t("Contradiction", "Противоречие"),
                    "unknown": t("Unverified", "Не подтверждено"),
                }[criterion["relation"]]
                add("bullet", criterion["requested"] + " — " + label)
                if criterion["quote"]:
                    add("quote", criterion["quote"])
            if assessment["identity_status"] in {"unresolved", "conflicting"}:
                add(
                    "note",
                    t(
                        "Not included among matching profiles: required identity criteria are unresolved or contradicted. This card is retained as a research lead, not a found person.",
                        "Не входит в подходящие профили: обязательные критерии не подтверждены или противоречат источнику. Карточка сохранена как направление проверки, а не найденный человек.",
                    ),
                )
                add("link", source["url"])
                continue
        if assessment:
            add(
                "note",
                t(
                    "A local model reviewed claim attribution and clue support. This second pass can still be wrong and is not independent corroboration or an identity probability. Missing clues are not contradictions.",
                    "Локальная модель проверяет, кому относится утверждение и поддерживает ли цитата ориентир. Повторная проверка тоже может ошибаться и не является независимым подтверждением или вероятностью личности. Отсутствие сведений не означает противоречия.",
                ),
            )
            for clue in assessment["supported"]:
                add("bullet", t("Supported clue: ", "Поддержанный ориентир: ") + clue["text"])
            for clue in assessment["missing"]:
                add(
                    "bullet",
                    t("Not found in recorded quotes: ", "Не найдено в записанных цитатах: ") + clue["text"],
                )
            if assessment["review_outdated"]:
                add(
                    "warning",
                    t(
                        "User review predates the current criteria. Review again.",
                        "Пользовательская оценка относится к предыдущим критериям. Проверьте заново.",
                    ),
                )
        reviewed = assessment.get("model_reviewed", False) if assessment else False
        if not reviewed:
            add(
                "note",
                t(
                    "Semantic review is pending. Earlier extracted claims are withheld from the profile summary. Continue research to review them.",
                    "Смысловая проверка ещё не выполнена. Прежние извлечённые утверждения не включены в обзор профиля. Продолжите исследование для проверки.",
                ),
            )
        if assessment and assessment.get("note"):
            line(
                "AI interpretation (review required)", "Комментарий ИИ (требует проверки)", assessment["note"]
            )
            line(
                "Refers to claims",
                "Ссылается на утверждения",
                ", ".join(str(i + 1) for i in assessment["note_facts"]),
            )
        for flag in (assessment or {}).get("flags", []):
            add("warning", flag)
        if assessment and assessment.get("checked_facts"):
            add(
                "h2",
                t(
                    "Public work and education — sourced overview",
                    "Публичная деятельность и образование — обзор по источникам",
                ),
            )
        for f in (assessment or {}).get("checked_facts", []):
            add("fact", f"[{f['index'] + 1}] " + f["statement"])
            add("quote", f["quote"])
            add("link", source["url"])
        if assessment and assessment.get("withheld_count"):
            line(
                "Claims withheld from this overview",
                "Утверждений не включено в обзор",
                str(assessment["withheld_count"]),
            )
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
    if detail["queries"]:
        section("07 / Query log", "07 / Поисковые запросы")
    for q in detail["queries"]:
        add("h2", q["payload"]["query"])
        add("p", f"{q['payload'].get('language', 'en').upper()} / {translate(q['state'], lang)}")
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
