"""Human-reviewed cross-source hypotheses, with criterion-level provenance."""

from urllib.parse import urlsplit

from .identity import required, resolution
from .trails import relevant_links


def build_linkage(detail, decisions):
    candidates = {c["id"]: c for c in detail["candidates"]}
    sources = {s["id"]: s for s in detail["sources"]}
    by_url = {url: s["id"] for s in detail["sources"] for url in [s["url"], *s.get("url_aliases", [])]}
    by_source = {}
    for member in candidates.values():
        by_source.setdefault(member["source_id"], []).append(member)
    revision = detail["revision"]
    decision_map = {(d["left_id"], d["right_id"]): d for d in decisions}
    proposals = {}
    for cid, candidate in candidates.items():
        a = candidate["assessment"]
        if (
            a["excluded"]
            or candidate["status"] == "rejected"
            or not a["model_reviewed"]
            or not a["name_quote"]
        ):
            continue
        source = sources[candidate["source_id"]]
        for link in relevant_links(source.get("links", []), [candidate["value"]["name"]]):
            target_id = by_url.get(link["url"])
            for other in by_source.get(target_id, []):
                b = other["assessment"]
                if other["source_id"] != target_id or other["source_id"] == candidate["source_id"]:
                    continue
                if (
                    b["excluded"]
                    or other["status"] == "rejected"
                    or not b["model_reviewed"]
                    or not b["name_quote"]
                ):
                    continue
                pair = tuple(sorted((cid, other["id"])))
                decision = decision_map.get(pair, {})
                proposals[pair] = {
                    "left_id": pair[0],
                    "right_id": pair[1],
                    "from_source": source["id"],
                    "to_source": target_id,
                    "context": link["context"],
                    "kind": link["kind"],
                    "status": decision.get("status", "unreviewed")
                    if decision.get("revision") == revision
                    else "unreviewed",
                    "stale": bool(decision) and decision.get("revision") != revision,
                }
    parent = {cid: cid for cid in candidates}

    def find(cid):
        while parent[cid] != cid:
            cid = parent[cid]
        return cid

    for p in proposals.values():
        if p["status"] == "confirmed":
            parent[find(p["right_id"])] = find(p["left_id"])
    components = {}
    for cid in candidates:
        components.setdefault(find(cid), []).append(cid)
    groups = []
    for ids in components.values():
        if len(ids) < 2:
            continue
        members = [candidates[cid] for cid in ids]
        checks = []
        for criterion in required(detail["brief"], include_clues=True):
            evidence = []
            for member in members:
                for row in member["assessment"]["identity_checks"]:
                    if row["field"] == criterion["field"] and row["relation"] != "unknown":
                        evidence.append(
                            row | {"candidate_id": member["id"], "source_id": member["source_id"]}
                        )
            relation = (
                "contradicts"
                if any(e["relation"] == "contradicts" for e in evidence)
                else "supports"
                if evidence
                else "unknown"
            )
            checks.append(criterion | {"relation": relation, "evidence": evidence})
        state = resolution(checks, all(m["assessment"]["name_compatible"] for m in members))
        if any(m["assessment"]["level"] == "conflicting" for m in members):
            state = "conflicting"
        # Conservative independence estimate: same host OR identical body connects a source family.
        member_sources = list({m["source_id"]: sources[m["source_id"]] for m in members}.values())
        families = []
        for source in member_sources:
            host = (urlsplit(source["url"]).hostname or "").removeprefix("www.")
            content = source.get("content_hash")
            matches = [f for f in families if host in f["hosts"] or content and content in f["hashes"]]
            family = {"hosts": {host}, "hashes": {content} if content else set()}
            for match in matches:
                family["hosts"].update(match["hosts"])
                family["hashes"].update(match["hashes"])
                families.remove(match)
            families.append(family)
        groups.append(
            {
                "id": min(ids),
                "candidate_ids": sorted(ids),
                "identity_status": state,
                "identity_checks": checks,
                "source_families": len(families),
                "source_count": len(member_sources),
                "revision": revision,
            }
        )
    return {"proposals": list(proposals.values()), "groups": groups}
