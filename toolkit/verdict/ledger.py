from __future__ import annotations

from .schemas import LedgerRow, Status


def merge(
    claims,
    evidence,
    verdicts: dict,
    challenges: dict,
    rebuttals: dict | None = None,
) -> list[LedgerRow]:
    """verdicts[claim_id] = {status, rationale, judged_by}; challenges[claim_id] = {reason, rebutted: bool}.
    Rules:
    1. No evidence link on any row => force UNVERIFIED.
    2. Any evidence with supports=CONTRADICTED and agent said VERIFIED => CONTRADICTED (code wins).
    3. Skeptic challenge not rebutted => downgrade VERIFIED to UNVERIFIED.
    """
    rows = []
    ev_by = {}
    for e in evidence:
        ev_by.setdefault(e.claim_id, []).append(e)
    rebuttals = rebuttals or {}
    for c in claims:
        v = verdicts.get(c.id, {})
        status_value = v.get("status", "UNVERIFIED")
        status = Status(status_value)
        links = [e.link for e in ev_by.get(c.id, []) if e.link]
        if not links:
            status = Status.UNVERIFIED if status != Status.NOT_CHECKABLE else status
        rebuttal = rebuttals.get(c.id)
        if rebuttal and rebuttal.get("new_status"):
            status = Status(rebuttal["new_status"])
        ch = challenges.get(c.id)
        if ch and not ch.get("rebutted") and status == Status.VERIFIED:
            status = Status.UNVERIFIED
        if (
            any(e.supports == Status.CONTRADICTED for e in ev_by.get(c.id, []))
            and status != Status.NOT_CHECKABLE
        ):
            status = Status.CONTRADICTED
        rows.append(
            LedgerRow(
                c.id,
                c.pr,
                c.text,
                status,
                v.get("rationale", ""),
                links,
                v.get("judged_by", "code"),
            )
        )
    return rows
