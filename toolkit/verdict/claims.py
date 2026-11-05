"""Heuristic claim extraction. Candidates only: the Examiner agent decides what matters."""

from __future__ import annotations

import re

from .schemas import Claim

_RULES = [
    (
        "tests",
        re.compile(
            r"(?i)[^.\n]*\b\d+\s+(?:focused\s+|python\s+|core\s+)?tests?\b[^.\n]*(?:pass|green)[^.\n]*"
        ),
    ),
    ("tests", re.compile(r"(?i)[^.\n]*\b(?:all|tests?)\s+(?:pass|passed|passing|green)\b[^.\n]*")),
    (
        "lint",
        re.compile(r"(?i)[^.\n]*\b(?:ruff|mypy|lint|typecheck)\b[^.\n]*(?:pass|clean|ok)[^.\n]*"),
    ),
    (
        "access_level",
        re.compile(r"(?i)[^.\n]*\b(?:read-only|write-capable|least[- ]privilege)\b[^.\n]*"),
    ),
    (
        "e2e",
        re.compile(
            r"(?i)[^.\n]*\b(?:end-to-end|e2e|live (?:sign-in|connection)|works with)\b[^.\n]*"
        ),
    ),
    (
        "self_disclosed_gap",
        re.compile(
            r"(?i)[^.\n]*\b(?:not yet|follow-up|follow up|outstanding|remain(?:s)? (?:a )?draft|does not yet|cannot yet|blocked)\b[^.\n]*"
        ),
    ),
]


def extract(pr_number: int, body: str) -> list[Claim]:
    seen: set[tuple[str, str]] = set()
    out: list[Claim] = []
    for kind, rx in _RULES:
        for m in rx.finditer(body or ""):
            text = " ".join(m.group(0).split()).strip(" -*•#`")
            if len(text) < 12 or (kind, text) in seen:
                continue
            seen.add((kind, text))
            out.append(
                Claim(
                    id=f"{pr_number}-{len(out) + 1:02d}",
                    pr=pr_number,
                    text=text,
                    kind=kind,
                    source_quote=text,
                )
            )
    return out
