from ..claims import gap_hints
from ..schemas import Claim, Evidence, Status


def check_policy(
    claim: Claim,
    pr_draft: bool,
    pr_url: str,
    pr_body: str = "",
) -> list[Evidence]:
    out: list[Evidence] = []
    body = pr_body.lower()
    hits = gap_hints(pr_body)
    if claim.kind == "e2e" and hits:
        out.append(
            Evidence(
                claim.id,
                "policy",
                f"PR body contains gap language: {', '.join(hits)}",
                pr_url,
                Status.CONTRADICTED,
            )
        )
    if claim.kind == "access_level":
        conflicting_write = any(
            word in body for word in ("write", "mutate", "create", "delete", "update")
        )
        if "read-only" in body and conflicting_write:
            out.append(
                Evidence(
                    claim.id,
                    "policy",
                    "PR is described as read-only but also mentions write-capable operations",
                    pr_url,
                    Status.CONTRADICTED,
                )
            )
        else:
            out.append(
                Evidence(
                    claim.id,
                    "policy",
                    "PR access-level wording checked against PR body",
                    pr_url,
                    Status.UNVERIFIED,
                )
            )
    if pr_draft:
        out.append(Evidence(claim.id, "policy", "PR is a draft", pr_url, Status.UNVERIFIED))
    return out
