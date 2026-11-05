from ..schemas import Claim, Evidence, Status


def check_ci(gh, claim: Claim, head_sha: str, pr_url: str) -> list[Evidence]:
    """For kind in (tests, lint): compare the claim to real check-run conclusions on head_sha.
    TODO: gh.check_runs(head_sha) -> any failure => CONTRADICTED; none exist => UNVERIFIED;
    all success => VERIFIED. Always set link=f"{pr_url}/checks". Note: 'action_required' != pass."""
    if claim.kind not in ("tests", "lint"):
        return []
    return [Evidence(claim.id, "ci", "not implemented", "", Status.UNVERIFIED)]
