from __future__ import annotations

import re

from .schemas import PR, CaseFile

_CLOSES = r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)"


def refs_issue(pr_title: str, pr_body: str, issue: int) -> bool:
    """True if the PR links the issue: 'Closes #n', title '(#n)', or explicit '#n' in title."""
    n = str(issue)
    if re.search(rf"(?i)\b{_CLOSES}\s+#{n}\b", pr_body or ""):
        return True
    # body-only passing mention is NOT enough; Clerk flags these as "unclear"
    return bool(re.search(rf"\(#{n}\)|\B#{n}\b", pr_title or ""))


def build(gh, issue: int) -> CaseFile:
    i = gh.issue(issue)
    case = CaseFile(
        issue=issue,
        issue_title=i["title"],
        issue_body=i.get("body") or "",
        source="fixture" if gh.offline else "live",
    )
    for item in gh.search_prs_mentioning(issue):
        p = gh.pr(item["number"])
        if not refs_issue(p["title"], p.get("body") or "", issue):
            continue  # TODO: collect into case.unclear for the Clerk to mention
        case.prs.append(
            PR(
                number=p["number"],
                title=p["title"],
                author=p["user"]["login"],
                state="merged" if p.get("merged") else p["state"],
                draft=p.get("draft", False),
                head_sha=p["head"]["sha"],
                body=p.get("body") or "",
                url=p["html_url"],
                updated_at=p.get("updated_at", ""),
            )
        )
    return case
