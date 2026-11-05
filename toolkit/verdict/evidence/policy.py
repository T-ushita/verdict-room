from ..schemas import Claim, Evidence, Status

# Phrases that, in a PR body, mean 'this does not work end to end yet'
GAP_HINTS = ("not yet", "follow-up", "remain a draft", "blocked", "rejects", "key_never_expires")


def check_policy(claim: Claim, pr_draft: bool, pr_url: str) -> list[Evidence]:
    """Cheap, deterministic flags.
    - self_disclosed_gap claims are CONTRADICTED-evidence against any e2e claim in the same PR.
    - draft PR => note it; a draft cannot be 'ready'.
    - access_level: if the body says 'read-only' AND the same body mentions write/mutate tools => flag.
    TODO: implement; secret-pattern scan over diff lives here too (use redact patterns)."""
    out: list[Evidence] = []
    if claim.kind == "self_disclosed_gap":
        out.append(
            Evidence(claim.id, "policy", "PR discloses its own gap", pr_url, Status.CONTRADICTED)
        )
    if pr_draft:
        out.append(Evidence(claim.id, "policy", "PR is a draft", pr_url, Status.UNVERIFIED))
    return out
