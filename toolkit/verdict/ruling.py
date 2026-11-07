"""The ONLY module allowed to write to GitHub. Guarded by an approval gate."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path


def draft_hash(draft: str) -> str:
    return hashlib.sha256(draft.encode()).hexdigest()[:12]


def write_approval(case_dir: Path, draft: str, approved_by: str) -> Path:
    p = case_dir / "approval.json"
    p.write_text(
        json.dumps(
            {
                "approved_by": approved_by,
                "draft_hash": draft_hash(draft),
                "human_comments": "",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return p


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
        text = "\n".join(lines).strip() + "\n"
        pr_draft_path = drafts_dir / f"{pr_number}.md"
        if pr_draft_path.exists():
            text = pr_draft_path.read_text(encoding="utf-8")
            text = text.replace("â€”", "-").replace("â€“", "-").replace("—", "-").replace("–", "-")
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
            for approval_path in approvals_dir.glob("*.json"):
                pr_approval = json.loads(approval_path.read_text(encoding="utf-8"))
                pr = pr_approval.get("pr")
                pr_draft = case_dir / "drafts" / f"{pr}.md"
                if pr_draft.exists() and pr_approval.get("draft_hash") == draft_hash(
                    pr_draft.read_text(encoding="utf-8")
                ):
                    continue
                return False, f"draft changed after approval for PR #{pr}"
        else:
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
    token = os.environ.get("GITHUB_WRITE_TOKEN", "")
    if not token:
        return "DRY RUN (GITHUB_WRITE_TOKEN is not set)"
    repo = os.environ["VERDICT_POST_REPO"]
    api = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    approvals_dir = case_dir / "approvals"
    posted: list[str] = []

    if approvals_dir.exists():
        for approval_path in sorted(approvals_dir.glob("*.json")):
            approval = json.loads(approval_path.read_text(encoding="utf-8"))
            pr = approval["pr"]
            pr_draft = (case_dir / "drafts" / f"{pr}.md").read_text(encoding="utf-8")
            if draft_hash(pr_draft) != approval["draft_hash"]:
                return f"DRY RUN (approval draft changed for PR #{pr})"

    issue_draft = (case_dir / "drafts" / "issue.md").read_text(encoding="utf-8")
    issue = json.loads((case_dir / "casefile.json").read_text(encoding="utf-8"))["issue"]
    payloads: list[tuple[str, str]] = [(f"{api}/{issue}/comments", issue_draft)]
    if approvals_dir.exists():
        payloads.extend(
            (
                f"{api}/{approval_path.stem}/comments",
                (case_dir / "drafts" / f"{approval_path.stem}.md").read_text(encoding="utf-8"),
            )
            for approval_path in sorted(approvals_dir.glob("*.json"))
        )

    for url, body in payloads:
        request = urllib.request.Request(
            url,
            data=json.dumps({"body": body}).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                result = json.loads(response.read().decode("utf-8"))
                posted.append(result.get("html_url", url))
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            json.JSONDecodeError,
        ) as exc:
            return f"DRY RUN (GitHub comment failed: {type(exc).__name__})"
    return "POSTED:\n" + "\n".join(posted)
