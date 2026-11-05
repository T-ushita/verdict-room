import re

from ..schemas import Claim, Evidence, Status


def check_diff(gh, claim: Claim, pr_number: int, pr_url: str = "") -> list[Evidence]:
    link = f"{pr_url}/files" if pr_url else ""
    try:
        files = gh.pr_files(pr_number)
    except (FileNotFoundError, RuntimeError, KeyError):
        return [
            Evidence(
                claim.id,
                "diff",
                "PR file list unavailable or not recorded",
                link,
                Status.UNVERIFIED,
            )
        ]

    paths = [item.get("filename", "") for item in files if item.get("filename")]
    layers = [
        name
        for name, marker in (
            ("core", "core/"),
            ("gateway", "gateway/"),
            ("console", "console/"),
            ("docs", "docs/"),
            ("tests", "test"),
        )
        if any(marker in path.lower() for path in paths)
    ]
    test_paths = [
        path for path in paths if "/test" in path.lower() or path.lower().startswith("test")
    ]
    added_tests = sum(
        1
        for item in files
        for line in item.get("patch", "").splitlines()
        if line.startswith("+") and re.match(r"\+\s*(?:async\s+)?def\s+test_", line)
    )
    details = (
        f"Layers touched: {', '.join(layers) or 'none detected'}; "
        f"test files: {len(test_paths)}; added def test_ lines: {added_tests}"
    )
    status = Status.UNVERIFIED
    if claim.kind == "e2e":
        integration_paths = [
            path
            for path in test_paths
            if any(marker in path.lower() for marker in ("e2e", "integration", "live", "connector"))
        ]
        details += (
            "; integration/e2e test path present"
            if integration_paths
            else "; no integration/e2e test path detected"
        )
        if integration_paths:
            status = Status.UNVERIFIED
    return [Evidence(claim.id, "diff", details, link, status)]
