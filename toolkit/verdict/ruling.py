"""The ONLY module allowed to write to GitHub. Guarded by an approval gate."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


def draft_hash(draft: str) -> str:
    return hashlib.sha256(draft.encode()).hexdigest()[:12]


def write_approval(case_dir: Path, draft: str, approved_by: str) -> Path:
    p = case_dir / "approval.json"
    p.write_text(json.dumps({"approved_by": approved_by, "draft_hash": draft_hash(draft)}))
    return p


def gate_open(
    case_dir: Path,
    draft: str,
    live_flag: bool,
    target_repo: str | None = None,
) -> tuple[bool, str]:
    if os.environ.get("VERDICT_LIVE_POST") != "1":
        return False, "VERDICT_LIVE_POST is not 1"
    if not live_flag:
        return False, "--live not passed"
    a = case_dir / "approval.json"
    if not a.exists():
        return False, "no approval.json"
    if json.loads(a.read_text()).get("draft_hash") != draft_hash(draft):
        return False, "draft changed after approval"
    upstream_repo = os.environ.get("VERDICT_REPO", "")
    post_repo = os.environ.get("VERDICT_POST_REPO", "")
    if not post_repo:
        return False, "VERDICT_POST_REPO is not set"
    if not upstream_repo:
        return False, "VERDICT_REPO is not set"
    target_repo = target_repo or post_repo
    if target_repo != post_repo:
        return False, "target repo does not equal VERDICT_POST_REPO"
    if post_repo == upstream_repo and os.environ.get("VERDICT_ALLOW_UPSTREAM_POST") != "1":
        return False, "target repo matches upstream; explicit override is required"
    return True, "ok"


def post(case_dir: Path, draft: str, live_flag: bool) -> str:
    ok, why = gate_open(case_dir, draft, live_flag)
    if not ok:
        return f"DRY RUN ({why}):\n{draft}"
    if not os.environ.get("GITHUB_WRITE_TOKEN"):
        return "DRY RUN (GITHUB_WRITE_TOKEN is not set)"
    # TODO: POST comments with GITHUB_WRITE_TOKEN.
    # Target repo must equal VERDICT_POST_REPO and be the sandbox fork for the demo.
    raise NotImplementedError("live posting not implemented")
