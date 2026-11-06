from __future__ import annotations

import json
from pathlib import Path

from .schemas import LedgerRow, Status


def load_agent_json(
    case_dir: Path,
    filename: str,
    required_fields: tuple[str, ...],
) -> dict:
    path = case_dir / filename
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{filename}: malformed JSON at line {exc.lineno}, column {exc.colno}"
        ) from exc
    if not isinstance(payload, dict):
        raise TypeError(f"{filename}: expected a JSON object keyed by claim id")
    for claim_id, value in payload.items():
        if not isinstance(claim_id, str) or not claim_id.strip():
            raise ValueError(f"{filename}: claim id must be a non-empty string")
        if not isinstance(value, dict):
            raise TypeError(f"{filename}: entry {claim_id!r} must be a JSON object")
        for field in required_fields:
            if field not in value:
                raise ValueError(f"{filename}: entry {claim_id!r} is missing {field!r}")
    return payload


def validate_agent_inputs(case_dir: Path, claim_ids: set[str]) -> tuple[dict, dict, dict]:
    verdicts = load_agent_json(case_dir, "verdicts.json", ("status", "rationale", "judged_by"))
    challenges = load_agent_json(case_dir, "challenges.json", ("reason", "rebutted"))
    rebuttals = load_agent_json(case_dir, "rebuttals.json", ("rebuttal",))
    valid_statuses = {status.value for status in Status}

    for claim_id, value in verdicts.items():
        if claim_id not in claim_ids:
            raise ValueError(f"verdicts.json: unknown claim id {claim_id!r}")
        if value["status"] not in valid_statuses:
            raise ValueError(f"verdicts.json: invalid status {value['status']!r}")
        for field in ("rationale", "judged_by"):
            if not isinstance(value[field], str) or not value[field].strip():
                raise ValueError(f"verdicts.json: {field} must be non-empty for {claim_id!r}")

    for claim_id, value in challenges.items():
        if claim_id not in claim_ids:
            raise ValueError(f"challenges.json: unknown claim id {claim_id!r}")
        if not isinstance(value["reason"], str) or not value["reason"].strip():
            raise ValueError(f"challenges.json: reason must be non-empty for {claim_id!r}")
        if not isinstance(value["rebutted"], bool):
            raise TypeError(f"challenges.json: rebutted must be boolean for {claim_id!r}")

    for claim_id, value in rebuttals.items():
        if claim_id not in claim_ids:
            raise ValueError(f"rebuttals.json: unknown claim id {claim_id!r}")
        if not isinstance(value["rebuttal"], str) or not value["rebuttal"].strip():
            raise ValueError(f"rebuttals.json: rebuttal must be non-empty for {claim_id!r}")
        if "new_status" in value and value["new_status"] not in valid_statuses:
            raise ValueError(
                f"rebuttals.json: invalid new_status {value['new_status']!r} for {claim_id!r}"
            )
    return verdicts, challenges, rebuttals


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
