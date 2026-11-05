from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class Status(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED = "CONTRADICTED"
    NOT_CHECKABLE = "NOT_CHECKABLE"


@dataclass
class PR:
    number: int
    title: str
    author: str
    state: str  # open | closed | merged
    draft: bool
    head_sha: str
    body: str
    url: str
    updated_at: str = ""


@dataclass
class CaseFile:
    issue: int
    issue_title: str
    issue_body: str
    prs: list[PR] = field(default_factory=list)
    source: str = "live"  # live | fixture  (surface this in the UI)


@dataclass
class Claim:
    id: str  # e.g. "1436-03"
    pr: int
    text: str
    kind: str  # tests | lint | access_level | e2e | scope | self_disclosed_gap | other
    source_quote: str


@dataclass
class Evidence:
    claim_id: str
    check: str  # ci | diff | tests | policy
    result: str  # human-readable fact
    link: str  # URL or file:line; empty means no evidence
    supports: Status | None = None


@dataclass
class LedgerRow:
    claim_id: str
    pr: int
    claim: str
    status: Status
    rationale: str
    evidence_links: list[str]
    judged_by: str


def to_dict(obj):
    d = asdict(obj)
    return _enum_to_str(d)


def _enum_to_str(x):
    if isinstance(x, dict):
        return {k: _enum_to_str(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_enum_to_str(v) for v in x]
    return x.value if isinstance(x, Enum) else x
