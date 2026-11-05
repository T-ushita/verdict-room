from ..schemas import Claim, Evidence


def check_diff(gh, claim: Claim, pr_number: int) -> list[Evidence]:
    """TODO: use gh.pr_files(pr_number). Facts to emit:
    - layers touched (core/, gateway/, console/, docs/)
    - test files added/changed and count of `def test_` added lines
    - for claim.kind == 'e2e': is there ANY test touching an integration/e2e path? if none => UNVERIFIED
    link to f"{pr_url}/files"."""
    return []
