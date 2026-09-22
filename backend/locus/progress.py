"""Run-control decisions from actual work and limits, not generated narration."""


def continuation_state(detail):
    budget, stats, queue = detail["brief"]["budget"], detail["stats"], detail["queue"]
    exhausted = [
        field
        for field, used, limit in (
            ("time", detail["active_seconds"], budget["minutes"] * 60),
            ("queries", stats["queries"], budget["queries"]),
            ("pages", stats["pages"], budget["pages"]),
            ("rounds", detail["rounds"], budget["rounds"]),
        )
        if used >= limit
    ]
    # A network limit does not prevent reviewing a page already in the project.
    retryable = detail.get("retryable_model_steps", 0)
    can_review = queue["review"] or queue["analyze"] or detail["conclusion"]["pending_cards"] or retryable
    can_read = queue["fetch"] and "pages" not in exhausted
    can_search = queue["search"] and not {"pages", "queries"}.intersection(exhausted)
    can_plan = not {"pages", "queries", "rounds"}.intersection(exhausted)
    blocked = (
        ["time"]
        if "time" in exhausted
        else (exhausted if not (can_review or can_read or can_search or can_plan) else [])
    )
    return {"blocked_by": blocked, "exhausted": exhausted, "pending_steps": sum(queue.values()) + retryable}
