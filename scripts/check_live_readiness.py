import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "toolkit"))

from verdict.ruling import gate_open, normalize_draft_text

issue = 825
case_dir = repo_root / "cases" / f"issue-{issue}"
draft_path = case_dir / "ruling.draft.md"
draft = draft_path.read_text(encoding="utf-8") if draft_path.exists() else ""
ok, reason = gate_open(case_dir, normalize_draft_text(draft), True)

print(f"Gate: {'OPEN' if ok else 'BLOCKED'}")
print(f"Reason: {reason}")
print("Write token: " + ("SET" if os.environ.get("GITHUB_WRITE_TOKEN", "").strip() else "NOT SET"))
