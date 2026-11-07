"""Heuristic claim extraction. Candidates only: the Examiner decides what matters."""

from __future__ import annotations

import re

from .schemas import Claim

_RULES = [
    (
        "tests",
        re.compile(
            r"(?i)[^.\n]*\b\d+\s+(?:focused\s+|connection\s+|connector\/broker\/catalog\s+|python\s+|core\s+)?tests?\b[^.\n]*(?:pass(?:ed)?|green|errored)[^.\n]*"
        ),
    ),
    (
        "tests",
        re.compile(
            r"(?i)[^.\n]*\b\d+\s+(?:focused\s+|python\s+|core\s+)?tests?\b[^.\n]*(?:pass|green)[^.\n]*"
        ),
    ),
    (
        "tests",
        re.compile(r"(?i)[^.\n]*\b(?:all|tests?)\s+(?:pass|passed|passing|green)\b[^.\n]*"),
    ),
    (
        "tests",
        re.compile(
            r"(?i)[^.\n]*\b\d+\s+(?:focused\s+|connection\s+|connector\/broker\/catalog\s+|python\s+|core\s+)?tests?\b[^.\n]*(?:fail(?:ed)?|errored|error(?:s)?)[^.\n]*"
        ),
    ),
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
        re.compile(r"(?i)[^.\n]*\b(?:end-to-end|e2e|works with)\b[^.\n]*"),
    ),
    (
        "e2e",
        re.compile(
            r"(?i)[^.\n]*\b(?:identity|connection|authentication)\s+(?:was\s+)?verified\s+via\b[^.\n]*"
        ),
    ),
]

_GAP_HINTS = (
    "not yet",
    "follow-up",
    "remain a draft",
    "blocked",
    "rejects",
    "key_never_expires",
    "no agent grant",
)


def gap_hints(body: str) -> list[str]:
    """Return deterministic gap phrases found in a PR body."""
    text = body or ""
    return [hint for hint in _GAP_HINTS if hint.lower() in text.lower()]


def extract(pr_number: int, body: str) -> list[Claim]:
    seen: set[tuple[str, str]] = set()
    out: list[Claim] = []
    for kind, pattern in _RULES:
        for match in pattern.finditer(body or ""):
            sentence = match.group(0)
            if kind == "e2e" and re.search(
                r"(?i)\b(?:not yet|does not yet|cannot yet|no .*yet)\b",
                sentence,
            ):
                continue
            text = " ".join(sentence.split()).strip(" -*•#`")
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

    if re.search(
        r"(?i)\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#\d+\b",
        body or "",
    ):
        out.append(
            Claim(
                id=f"{pr_number}-{len(out) + 1:02d}",
                pr=pr_number,
                text="This PR delivers a working integration for the linked issue.",
                kind="e2e",
                source_quote="Implicit claim from PR issue linkage",
            )
        )
    hints = gap_hints(body)
    for hint in hints:
        out.append(
            Claim(
                id=f"{pr_number}-{len(out) + 1:02d}",
                pr=pr_number,
                text=f"Self-disclosed gap: {hint}",
                kind="self_disclosed_gap",
                source_quote=f"PR body gap hint: {hint}",
            )
        )
    return out
