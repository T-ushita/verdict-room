from ..schemas import Claim, Evidence, Status


def check_ci(gh, claim: Claim, head_sha: str, pr_url: str) -> list[Evidence]:
    """Compare CI check conclusions to a test or lint claim."""
    if claim.kind not in ("tests", "lint"):
        return []
    link = f"{pr_url}/checks"
    try:
        payload = gh.check_runs(head_sha)
    except (FileNotFoundError, RuntimeError, KeyError):
        return [
            Evidence(
                claim.id, "ci", "Check runs unavailable or not recorded", link, Status.UNVERIFIED
            )
        ]
    runs = payload.get("check_runs", [])
    if not runs:
        return [
            Evidence(claim.id, "ci", "No check runs exist for head SHA", link, Status.UNVERIFIED)
        ]
    conclusions = [run.get("conclusion") for run in runs]
    failed = {"failure", "timed_out", "cancelled", "stale", "startup_failure"}
    if any(value in failed for value in conclusions):
        return [
            Evidence(claim.id, "ci", "One or more check runs failed", link, Status.CONTRADICTED)
        ]
    if all(value == "success" for value in conclusions):
        return [
            Evidence(claim.id, "ci", "All check runs succeeded for head SHA", link, Status.VERIFIED)
        ]
    return [
        Evidence(claim.id, "ci", "Check runs are incomplete or not passed", link, Status.UNVERIFIED)
    ]
