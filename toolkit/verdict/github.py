"""Read-only GitHub client. No write methods belong in this module."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.github.com"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


class GitHub:
    def __init__(self, repo: str, offline: bool = False):
        self.repo, self.offline = repo, offline
        self.token = os.environ.get("GITHUB_TOKEN", "")

    def _get(self, path: str):
        if self.offline:
            base = path.split("?", 1)[0]
            if base == "/search/issues":
                query = path.split("?", 1)[1]
                issue_match = query.split("%23", 1)[1].split("+", 1)[0] if "%23" in query else ""
                if issue_match:
                    base = f"/search/issues__{issue_match}"
            fixture = FIXTURES / (base.strip("/").replace("/", "__") + ".json")
            if not fixture.exists():
                raise FileNotFoundError(f"Missing offline fixture: {fixture.relative_to(FIXTURES)}")
            return json.loads(fixture.read_text())

        request = urllib.request.Request(
            API + path, headers={"Accept": "application/vnd.github+json"}
        )
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")

        last_error = None
        for attempt in range(2):
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    return json.load(response)
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code == 403:
                    raise RuntimeError(
                        "GitHub API rate limit or permissions error (read-only token required)"
                    ) from exc
                if exc.code >= 500 and attempt == 0:
                    time.sleep(1)
                    continue
                raise
            except urllib.error.URLError as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(1)
                    continue
                raise
        raise RuntimeError(f"GitHub request failed after one retry: {last_error}")

    def issue(self, n: int) -> dict:
        return self._get(f"/repos/{self.repo}/issues/{n}")

    def pr(self, n: int) -> dict:
        return self._get(f"/repos/{self.repo}/pulls/{n}")

    def pr_files(self, n: int) -> list[dict]:
        return self._get(f"/repos/{self.repo}/pulls/{n}/files?per_page=100")

    def check_runs(self, sha: str) -> dict:
        return self._get(f"/repos/{self.repo}/commits/{sha}/check-runs")

    def search_prs_mentioning(self, issue: int) -> list[dict]:
        return self._get(f"/search/issues?q=repo:{self.repo}+is:pr+%23{issue}+in:title,body")[
            "items"
        ]
