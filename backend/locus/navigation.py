"""Choose observed links using the current identity decision, not name frequency."""

import re

from .names import variants
from .trails import relevant_links


def source_identity(detail, source_id):
    records = [c for c in detail["candidates"] if c["source_id"] == source_id]
    usable = [c for c in records if c["status"] != "rejected" and not c["assessment"]["excluded"]]
    if records and not usable:
        return "excluded"
    if any(c["assessment"]["identity_status"] == "eligible" for c in usable):
        return "eligible"
    ids = {c["id"] for c in usable}
    if any(
        g["identity_status"] == "eligible" and ids.intersection(g["candidate_ids"])
        for g in detail.get("linkage", {}).get("groups", [])
    ):
        return "eligible"
    if usable and all(c["assessment"]["identity_status"] == "conflicting" for c in usable):
        return "conflicting"
    if any(c["assessment"]["identity_status"] == "no_constraints" for c in usable):
        return "no_constraints"
    return "unresolved"


def identity_navigation(link):
    if link.get("kind") == "declared_same_as":
        return True
    # A named link to a professional profile can carry the missing country/school.
    # Preserve pre-0.7 saved links without anchor metadata; relevant_links still
    # requires the target name in this exact link's context.
    profile = r"(?i)(?:(?:my|professional|public)\s+)?(?:profile|portfolio|профиль|портфолио|профіль)"
    if link.get("kind") == "hyperlink":
        label = link.get("label") or link.get("context", "").rsplit(":", 1)[-1].strip()
        return bool(re.fullmatch(profile, label))
    # Profile navigation also includes portfolios/publication lists. Those are
    # useful after a match, but not for expanding an unconfirmed namesake.
    label = link.get("context", "").rsplit("→", 1)[-1].strip()
    return link.get("kind") == "profile_navigation" and bool(
        re.fullmatch(
            r"(?i)(?:(?:my|brief|professional|public)\s+)?(?:bio(?:graphy)?|resume|résumé|cv|profile|portfolio|about(?: me)?|биография|резюме|профиль|профіль|портфолио|про мене|о себе)",
            label,
        )
    )


def planned_trails(detail, source, brief):
    state = source_identity(detail, source["id"])
    if state in {"excluded", "conflicting"}:
        return []
    links = source.get("links", [])
    if state not in {"eligible", "no_constraints"}:
        links = [link for link in links if identity_navigation(link)]
    selected = relevant_links(
        links,
        [v["name"] for v in variants(brief)],
        brief.include_domains,
        brief.exclude_domains,
    )
    # A small, bounded route to a bio/profile can establish missing criteria.
    # Never automatically enumerate a namesake's books, works or other mentions.
    return selected if state in {"eligible", "no_constraints"} else selected[:2]
