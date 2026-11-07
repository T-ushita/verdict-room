from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from .casefile import build
from .claims import extract
from .evidence import check_ci, check_diff, check_policy, check_test_files
from .ledger import merge, validate_agent_inputs
from .schemas import Claim, Evidence, Status, to_dict

_ISSUE_RE = re.compile(r"(?i)(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)")
_TITLE_ISSUE_RE = re.compile(r"(?:\(#(\d+)\)|#(\d+)\b)")


def issue_numbers(pr: dict) -> list[int]:
    numbers = {int(value) for value in _ISSUE_RE.findall(pr.get("body") or "")}
    for value in _TITLE_ISSUE_RE.findall(pr.get("title") or ""):
        numbers.update(int(item) for item in value if item)
    return sorted(numbers)


def pr_status(pr: dict) -> str:
    if pr.get("merged"):
        return "MERGED"
    if pr.get("draft"):
        return "BLOCKED_DRAFT"
    return (pr.get("state") or "open").upper()


def fingerprint(pr: dict) -> str:
    return "|".join(
        [
            str(pr.get("head", {}).get("sha", "")),
            str(pr.get("updated_at", "")),
            str(pr.get("state", "")),
            str(pr.get("draft", False)),
            str(pr.get("title", "")),
            str(pr.get("body") or ""),
        ]
    )


def category(issue_data: dict) -> str:
    labels = issue_data.get("labels", [])
    names = [label["name"] if isinstance(label, dict) else str(label) for label in labels]
    category_labels = [name for name in names if name.lower().startswith("category:")]
    return category_labels[0].split(":", 1)[1] if category_labels else "uncategorized"


def prepare_issue(gh, root: Path, issue: int, changed_pr_numbers: set[int]) -> None:
    case_dir = root / "cases" / "live" / f"issue-{issue}"
    case_dir.mkdir(parents=True, exist_ok=True)
    case = build(gh, issue)
    (case_dir / "casefile.json").write_text(
        json.dumps(
            {
                "issue": case.issue,
                "issue_title": case.issue_title,
                "issue_body": case.issue_body,
                "prs": [
                    {
                        "number": pr.number,
                        "title": pr.title,
                        "author": pr.author,
                        "state": pr.state,
                        "draft": pr.draft,
                        "head_sha": pr.head_sha,
                        "body": pr.body,
                        "url": pr.url,
                        "updated_at": pr.updated_at,
                    }
                    for pr in case.prs
                ],
                "source": case.source,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    claims_path = case_dir / "claims.json"
    existing_claims = (
        json.loads(claims_path.read_text(encoding="utf-8")) if claims_path.exists() else []
    )
    claims = [row for row in existing_claims if row.get("pr") not in changed_pr_numbers]
    for pr in case.prs:
        if pr.number in changed_pr_numbers:
            claims.extend(to_dict_claims(extract(pr.number, pr.body)))
    claims_path.write_text(
        json.dumps(claims, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    evidence_path = case_dir / "evidence.json"
    existing_evidence = (
        json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else []
    )
    claim_ids_for_changed_prs = {
        row["id"] for row in existing_claims if row.get("pr") in changed_pr_numbers
    }
    claim_ids_for_changed_prs.update(
        row["id"] for row in claims if row.get("pr") in changed_pr_numbers
    )
    evidence = [
        row for row in existing_evidence if row.get("claim_id") not in claim_ids_for_changed_prs
    ]
    prs = {pr.number: pr for pr in case.prs}
    for claim_data in claims:
        pr_number = claim_data["pr"]
        if pr_number not in changed_pr_numbers:
            continue
        matching = Claim(
            claim_data["id"],
            claim_data["pr"],
            claim_data["text"],
            claim_data["kind"],
            claim_data["source_quote"],
        )
        pr = prs[pr_number]
        pr_url = pr.url
        evidence.extend(
            evidence_row
            for row in check_ci(gh, matching, pr.head_sha, pr_url)
            for evidence_row in [to_dict_claims([row])[0]]
        )
        evidence.extend(
            evidence_row
            for row in check_diff(gh, matching, pr.number, pr_url)
            for evidence_row in [to_dict_claims([row])[0]]
        )
        evidence.extend(
            evidence_row
            for row in check_test_files(gh, matching, pr.number, pr_url)
            for evidence_row in [to_dict_claims([row])[0]]
        )
        evidence.extend(
            evidence_row
            for row in check_policy(matching, pr.draft, pr_url, pr.body)
            for evidence_row in [to_dict_claims([row])[0]]
        )
    evidence_path.write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    claim_ids = {item["id"] for item in claims}
    loaded_claims = [
        Claim(item["id"], item["pr"], item["text"], item["kind"], item["source_quote"])
        for item in claims
    ]
    loaded_evidence = []
    for item in evidence:
        loaded_evidence.append(
            Evidence(
                item["claim_id"],
                item["check"],
                item["result"],
                item["link"],
                Status(item["supports"]) if item.get("supports") else None,
            )
        )
    verdicts, challenges, rebuttals = validate_agent_inputs(case_dir, claim_ids)
    rows = merge(loaded_claims, loaded_evidence, verdicts, challenges, rebuttals)
    (case_dir / "ledger.json").write_text(
        json.dumps(
            [
                {
                    "claim_id": row.claim_id,
                    "pr": row.pr,
                    "claim": row.claim,
                    "status": row.status.value,
                    "rationale": row.rationale,
                    "evidence_links": row.evidence_links,
                    "judged_by": row.judged_by,
                }
                for row in rows
            ],
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def to_dict_claims(items) -> list[dict]:
    return [to_dict(item) for item in items]


def scan(
    gh,
    root: Path,
    repo: str,
    now: str | None = None,
) -> dict:
    state_path = root / "cases" / "pr-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    previous = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    previous_prs = previous.get("prs", {})
    timestamp = now or datetime.now(UTC).isoformat()
    current_prs: dict[str, dict] = {}
    changed: list[dict] = []
    unchanged: list[dict] = []
    affected_issues: set[int] = set()

    for pr in gh.list_prs():
        number = int(pr["number"])
        issues = issue_numbers(pr)
        issue_details = {}
        for issue_number in issues:
            issue_data = gh.issue(issue_number)
            issue_details[str(issue_number)] = {
                "state": issue_data.get("state", "open"),
                "category": category(issue_data),
            }
            affected_issues.add(issue_number)

        status = pr_status(pr)
        fp = fingerprint(pr)
        entry = {
            "number": number,
            "title": pr.get("title", ""),
            "status": status,
            "head_sha": pr.get("head", {}).get("sha", ""),
            "updated_at": pr.get("updated_at", ""),
            "last_seen_at": timestamp,
            "fingerprint": fp,
            "issues": issues,
            "issue_details": issue_details,
            "url": pr.get("html_url", ""),
        }
        prior = previous_prs.get(str(number))
        current_prs[str(number)] = entry
        item = {
            "number": number,
            "status": status,
            "issues": issues,
            "url": pr.get("html_url", ""),
            "title": pr.get("title", ""),
        }
        if prior is None:
            item["change"] = "NEW"
            changed.append(item)
        elif prior.get("fingerprint") != fp or prior.get("status") != status:
            item["change"] = "CHANGED"
            changed.append(item)
        else:
            unchanged.append(item)

    state = {
        "repo": repo,
        "scanned_at": timestamp,
        "prs": current_prs,
    }
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    summary = {
        "repo": repo,
        "scanned_at": timestamp,
        "changed_count": len(changed),
        "unchanged_count": len(unchanged),
        "changed": changed,
        "unchanged": unchanged,
        "affected_issues": sorted(affected_issues),
        "action_required": [
            item for item in changed if item["status"] in {"OPEN", "BLOCKED_DRAFT"}
        ],
    }
    summary_path = root / "cases" / "scan-summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    for item in changed:
        if item["status"] not in {"OPEN", "BLOCKED_DRAFT"}:
            continue
        for issue in item["issues"]:
            prepare_issue(gh, root, issue, {item["number"]})
    return summary
