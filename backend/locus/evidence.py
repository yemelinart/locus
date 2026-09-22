"""Explainable source support; no calibrated identity probability or automatic merge."""

import re
import unicodedata

from .identity import required, resolution
from .verification import AUDIT_METHOD
from .web import domain_allowed

LABELS = {
    "insufficient": ("Insufficient evidence", "Недостаточно свидетельств"),
    "limited": ("Limited support", "Слабая обоснованность"),
    "supported": ("Supporting clues", "Есть подтверждающие ориентиры"),
    "strong": ("Multiple supporting clues", "Несколько подтверждающих ориентиров"),
    "conflicting": ("Needs conflict review", "Нужно проверить противоречия"),
    "excluded": ("Archived by current filters", "В архиве по текущим фильтрам"),
}
CONCLUSIONS = {
    "not_started": ("Research has not started", "Исследование ещё не началось"),
    "no_accessible_sources": ("No readable sources yet", "Прочитанных источников пока нет"),
    "no_supported_findings": ("No supported match established", "Обоснованного совпадения пока нет"),
    "limited": ("Some findings, identity still unclear", "Сведения найдены, личность пока не установлена"),
    "possible": ("A promising match to review", "Есть совпадение, которое стоит проверить"),
    "multiple_candidates": ("Several candidate cards need review", "Несколько карточек требуют проверки"),
}


def contains(text, phrase):
    def norm(value):
        return " ".join(unicodedata.normalize("NFKC", value).casefold().split())

    return bool(re.search(r"(?<!\w)" + re.escape(norm(phrase)) + r"(?!\w)", norm(text)))


def assess(candidate, source, brief, revision):
    value = candidate["value"]
    facts = value.get("facts", [])
    audit = candidate.get("verification") or {}
    current = (
        audit.get("revision") == revision
        and audit.get("status") == "reviewed"
        and audit.get("method") == AUDIT_METHOD
    )
    checked = (
        [facts[i] | {"index": i} for i in audit.get("accepted_facts", []) if 0 <= i < len(facts)]
        if current
        else []
    )
    supplied_names = [brief["name"], *brief.get("aliases", []), *brief.get("previous_names", [])]
    name_quote = (
        audit.get("name_quote", "")
        if current
        else next((f["quote"] for f in facts if any(contains(f["quote"], n) for n in supplied_names)), "")
    )
    supported = audit.get("supported", []) if current and checked and name_quote else []
    conflicts = audit.get("conflicts", []) if current and name_quote else []
    matched = {c["index"] for c in [*supported, *conflicts]}
    missing = [c for i, c in enumerate(brief.get("evidence_clues", [])) if i not in matched]
    kinds = {c["kind"] for c in supported}
    level = "insufficient"
    if name_quote:
        level = "limited"
        if current and checked and audit.get("name_relation") in {"same_spelling", "plausible_variant"}:
            level = "strong" if len(kinds) >= 2 else "supported" if kinds else "limited"
    if conflicts or (current and audit.get("name_relation") == "different"):
        level = "conflicting"
    excluded = bool(source.get("url")) and not domain_allowed(
        source["url"], brief.get("include_domains", []), brief.get("exclude_domains", [])
    )
    if excluded:
        level = "excluded"
    checks = audit.get("identity_checks", []) if current else []
    # Rebuild from the brief so omitted/stale criteria cannot disappear from the gate.
    checks = [
        next(
            (c for c in checks if c["field"] == r["field"] and c["requested"] == r["requested"]),
            r | {"relation": "unknown", "quote": "", "observed": ""},
        )
        for r in required(brief, include_clues=True)
    ]
    identity_status = resolution(
        checks,
        bool(name_quote) and current and audit.get("name_relation") in {"same_spelling", "plausible_variant"},
    )
    if not excluded:
        if identity_status == "conflicting":
            level = "conflicting"
        elif identity_status == "unresolved":
            level = "limited" if name_quote else "insufficient"
        elif identity_status == "eligible" and level not in {"conflicting", "insufficient"}:
            level = "supported" if level == "limited" else level
    return {
        "name_compatible": bool(name_quote)
        and current
        and audit.get("name_relation") in {"same_spelling", "plausible_variant"},
        "identity_checks": checks,
        "identity_status": identity_status,
        "level": level,
        "name_quote": name_quote,
        "supported": supported,
        "missing": missing,
        "flags": [c["text"] + ": “" + c["quote"] + "”" for c in conflicts],
        "conflicts": conflicts,
        "excluded": excluded,
        "revision": revision,
        "review_outdated": candidate["status"] != "unreviewed"
        and candidate.get("review_revision", 1) < revision,
        "method": AUDIT_METHOD if current else "quote-only-pending-review",
        "model_reviewed": current,
        "audit_outdated": bool(audit) and not current,
        "checked_facts": checked,
        "withheld_count": len(facts) - len(checked),
        "note": audit.get("note", "") if current else "",
        "note_facts": audit.get("note_facts", []) if current else [],
    }


def conclusion(detail):
    candidates = [
        c for c in detail["candidates"] if c["status"] != "rejected" and not c["assessment"]["excluded"]
    ]
    eligible = [c for c in candidates if c["assessment"]["identity_status"] in {"eligible", "no_constraints"}]
    promising = [c for c in eligible if c["assessment"]["level"] in {"supported", "strong"}]
    groups = [g for g in detail.get("linkage", {}).get("groups", []) if g["identity_status"] == "eligible"]
    grouped_ids = {cid for g in groups for cid in g["candidate_ids"]}
    promising = [c for c in promising if c["id"] not in grouped_ids]
    checked = sum(
        len(c["assessment"]["checked_facts"]) for c in candidates if c in eligible or c["id"] in grouped_ids
    )
    state = "no_supported_findings"
    if not detail["stats"]["queries"] and not detail["sources"] and detail["status"] == "draft":
        state = "not_started"
    elif not any(s["status"] == "read" for s in detail["sources"]):
        state = "no_accessible_sources"
    elif len(promising) + len(groups) > 1:
        state = "multiple_candidates"
    elif promising or groups:
        state = "possible"
    elif checked:
        state = "limited"
    return {
        "linked_matches": len(groups),
        "unresolved_identity": sum(
            c["assessment"]["identity_status"] == "unresolved" and c["id"] not in grouped_ids
            for c in candidates
        ),
        "conflicting_identity": sum(c["assessment"]["identity_status"] == "conflicting" for c in candidates),
        "state": state,
        "provisional": detail["status"] in {"running", "queued", "paused"},
        "promising_ids": [c["id"] for c in promising],
        "reviewed_claims": checked,
        "pending_cards": sum(not c["assessment"]["model_reviewed"] for c in candidates),
        "conflicting_cards": sum(c["assessment"]["level"] == "conflicting" for c in candidates),
        "confirmed_cards": sum(
            c["status"] == "confirmed" and not c["assessment"]["review_outdated"] for c in candidates
        ),
        "read_sources": sum(s["status"] == "read" for s in detail["sources"]),
        "unavailable_sources": sum(s["status"] != "read" for s in detail["sources"]),
    }
