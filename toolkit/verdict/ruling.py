"""The ONLY module allowed to write to GitHub. Guarded by an approval gate."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from .redact import redact


def normalize_draft_text(draft: str) -> str:
    text = str(draft).replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("â€”", "-").replace("â€“", "-").replace("—", "-").replace("–", "-")
    return text.strip()


def draft_hash(draft: str) -> str:
    return hashlib.sha256(normalize_draft_text(draft).encode("utf-8")).hexdigest()[:12]


def write_approval(case_dir: Path, draft: str, approved_by: str) -> Path:
    normalized = normalize_draft_text(draft)
    p = case_dir / "approval.json"
    p.write_text(
        json.dumps(
            {
                "approved_by": approved_by,
                "draft_hash": draft_hash(normalized),
                "human_comments": "",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return p


def save_pr_approval(
    case_dir: Path,
    pr: int,
    draft: str,
    approver: str,
    outcome: str,
    human_comments: str = "",
) -> dict:
    normalized = normalize_draft_text(draft)
    drafts_dir = case_dir / "drafts"
    drafts_dir.mkdir(exist_ok=True)
    draft_path = drafts_dir / f"{pr}.md"
    draft_path.write_text(normalized + "\n", encoding="utf-8")

    timestamp = datetime.now(UTC).isoformat()
    approval = {
        "approver": approver,
        "outcome": outcome,
        "pr": pr,
        "draft_hash": draft_hash(normalized),
        "timestamp": timestamp,
        "human_comments": normalize_draft_text(human_comments),
    }
    approvals_dir = case_dir / "approvals"
    approvals_dir.mkdir(exist_ok=True)
    per_pr = approvals_dir / f"{pr}.json"
    per_pr.write_text(
        json.dumps(approval, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    case_dir.joinpath("approval.json").write_text(
        json.dumps(approval, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return approval


def save_issue_approval(
    case_dir: Path,
    draft: str,
    approver: str,
    outcome: str,
    human_comments: str = "",
) -> dict:
    normalized = normalize_draft_text(draft)
    drafts_dir = case_dir / "drafts"
    drafts_dir.mkdir(exist_ok=True)
    draft_path = drafts_dir / "issue.md"
    draft_path.write_text(normalized + "\n", encoding="utf-8")
    approval = {
        "approver": approver,
        "outcome": outcome,
        "pr": "issue",
        "draft_hash": draft_hash(normalized),
        "timestamp": datetime.now(UTC).isoformat(),
        "human_comments": normalize_draft_text(human_comments),
    }
    approvals_dir = case_dir / "approvals"
    approvals_dir.mkdir(exist_ok=True)
    (approvals_dir / "issue.json").write_text(
        json.dumps(approval, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return approval


def generate_drafts(case_dir: Path) -> dict[str, str]:
    casefile = json.loads((case_dir / "casefile.json").read_text(encoding="utf-8"))
    ledger = (
        json.loads((case_dir / "ledger.json").read_text(encoding="utf-8"))
        if (case_dir / "ledger.json").exists()
        else []
    )

    human_comments = ""
    approval_path = case_dir / "approval.json"
    if approval_path.exists():
        human_comments = str(
            json.loads(approval_path.read_text(encoding="utf-8")).get("human_comments", "")
        ).strip()

    drafts_dir = case_dir / "drafts"
    drafts_dir.mkdir(exist_ok=True)
    generated: dict[str, str] = {}

    for pr in casefile.get("prs", []):
        pr_number = int(pr["number"])
        rows = [row for row in ledger if row.get("pr") == pr_number]
        lines = [
            f"Verdict Room summary for #{pr_number} {pr.get('title', '')}",
            "",
            "Evidence-ledger findings:",
        ]
        if rows:
            for row in rows:
                links = ", ".join(row.get("evidence_links", []))
                lines.append(
                    f"- {row['claim_id']}: {row['status']} - {row['claim']}"
                    + (f"\n  Evidence: {links}" if links else "")
                )
        else:
            lines.append("- No evidence ledger rows available.")
        if human_comments:
            lines.extend(["", "Human maintainer notes:", human_comments])
        text = normalize_draft_text("\n".join(lines)) + "\n"
        pr_draft_path = drafts_dir / f"{pr_number}.md"
        if pr_draft_path.exists():
            text = normalize_draft_text(pr_draft_path.read_text(encoding="utf-8")) + "\n"
        else:
            pr_draft_path.write_text(text, encoding="utf-8")
        generated[str(pr_number)] = text

    issue_lines = [
        f"Verdict Room summary for issue #{casefile['issue']}: {casefile.get('issue_title', '')}",
        "",
        "The evidence ledger contains the following competing-PR findings:",
        "",
    ]
    for row in ledger:
        issue_lines.append(
            f"- PR #{row['pr']} - {row['claim_id']} {row['status']} - {row['claim']}"
        )
    if human_comments:
        issue_lines.extend(["", "Human maintainer notes:", human_comments])
    issue_text = "\n".join(issue_lines).strip() + "\n"
    (drafts_dir / "issue.md").write_text(issue_text, encoding="utf-8")
    generated["issue"] = issue_text

    aggregate = "\n\n".join(
        [generated["issue"], *(generated[str(pr["number"])] for pr in casefile.get("prs", []))]
    )
    (case_dir / "ruling.draft.md").write_text(aggregate, encoding="utf-8")
    return generated


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
    approval = json.loads(a.read_text(encoding="utf-8"))
    if approval.get("draft_hash") != draft_hash(draft):
        approvals_dir = case_dir / "approvals"
        if approvals_dir.exists() and any(approvals_dir.glob("*.json")):
            draft_matches_approval = False
            for approval_path in approvals_dir.glob("*.json"):
                pr_approval = json.loads(approval_path.read_text(encoding="utf-8"))
                pr = pr_approval.get("pr")
                pr_draft = case_dir / "drafts" / f"{pr}.md"
                if pr_draft.exists() and pr_approval.get("draft_hash") == draft_hash(
                    pr_draft.read_text(encoding="utf-8")
                ):
                    if draft_hash(draft) == draft_hash(pr_draft.read_text(encoding="utf-8")):
                        draft_matches_approval = True
                    continue
                return False, f"draft changed after approval for PR #{pr}"
            if not draft_matches_approval:
                return False, "draft changed after approval"
        else:
            return False, "draft changed after approval"
    upstream_repo = os.environ.get("VERDICT_REPO", "")
    post_repo = os.environ.get("VERDICT_POST_REPO", "")
    if not post_repo:
        return False, "VERDICT_POST_REPO is not set"
    if not upstream_repo:
        return False, "VERDICT_REPO is not set"
    post_issue = os.environ.get("VERDICT_POST_ISSUE", "")
    if not post_issue.isdigit():
        return False, "VERDICT_POST_ISSUE is not a numeric verdict-log issue"
    target_repo = target_repo or post_repo
    if target_repo != post_repo:
        return False, "target repo does not equal VERDICT_POST_REPO"
    if post_repo == upstream_repo and os.environ.get("VERDICT_ALLOW_UPSTREAM_POST") != "1":
        return False, "target repo matches upstream; explicit override is required"
    issue_approval_path = case_dir / "approvals" / "issue.json"
    issue_draft_path = case_dir / "drafts" / "issue.md"
    if not issue_approval_path.exists():
        return False, "no issue-level approval"
    issue_approval = json.loads(issue_approval_path.read_text(encoding="utf-8"))
    if not issue_draft_path.exists():
        return False, "issue draft missing"
    if issue_approval.get("draft_hash") != draft_hash(issue_draft_path.read_text(encoding="utf-8")):
        return False, "issue draft changed after approval"
    return True, "ok"


def post(case_dir: Path, draft: str, live_flag: bool) -> str:
    ok, why = gate_open(case_dir, draft, live_flag)
    if not ok:
        return f"DRY RUN ({why}):\n{draft}"
    token = os.environ.get("GITHUB_WRITE_TOKEN", "")
    if not token:
        return "DRY RUN (GITHUB_WRITE_TOKEN is not set)"
    repo = os.environ["VERDICT_POST_REPO"]
    issue_number = os.environ["VERDICT_POST_ISSUE"]
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
    write_token = token
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    headers["Authorization"] = "Bearer " + write_token
    request = urllib.request.Request(
        url,
        data=json.dumps({"body": draft}).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
            return "POSTED:\n" + result.get("html_url", url)
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        json.JSONDecodeError,
    ) as exc:
        return f"PARTIAL ({type(exc).__name__}: {redact(str(exc))})"
