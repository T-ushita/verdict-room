from ..schemas import Claim, Evidence, Status


def check_test_files(
    gh,
    claim: Claim,
    pr_number: int,
    pr_url: str = "",
) -> list[Evidence]:
    link = f"{pr_url}/files" if pr_url else ""
    try:
        files = gh.pr_files(pr_number)
    except (FileNotFoundError, RuntimeError, KeyError):
        return [
            Evidence(
                claim.id, "tests", "Test files unavailable or not recorded", link, Status.UNVERIFIED
            )
        ]

    test_files = [
        item["filename"]
        for item in files
        if item.get("filename")
        and ("/test" in item["filename"].lower() or item["filename"].lower().startswith("test"))
    ]
    status = Status.VERIFIED if test_files and claim.kind in {"tests", "e2e"} else Status.UNVERIFIED
    result = (
        f"Test files changed: {', '.join(test_files)}" if test_files else "No test files changed"
    )
    return [Evidence(claim.id, "tests", result, link, status)]
