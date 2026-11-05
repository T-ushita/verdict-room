from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from . import casefile
from . import claims as claims_mod
from .github import GitHub
from .schemas import to_dict

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "cases"


def _case_dir(issue: int, offline: bool | None = None) -> Path:
    if offline is None:
        offline_file = CASES / f"issue-{issue}" / "casefile.json"
        live_file = CASES / "live" / f"issue-{issue}" / "casefile.json"
        if live_file.exists():
            offline = False
        elif offline_file.exists():
            offline = json.loads(offline_file.read_text()).get("source") == "fixture"
        else:
            offline = False
    d = CASES / f"issue-{issue}" if offline else CASES / "live" / f"issue-{issue}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cmd_case(a):
    gh = GitHub(os.environ.get("VERDICT_REPO", "sandbox-quantum/switch"), offline=a.offline)
    case = casefile.build(gh, a.issue)
    (_case_dir(a.issue, offline=a.offline) / "casefile.json").write_text(
        json.dumps(to_dict(case), indent=2)
    )
    print(
        f"issue #{a.issue}: {len(case.prs)} PR(s): {[p.number for p in case.prs]} [{case.source}]"
    )


def cmd_claims(a):
    d = _case_dir(a.issue, offline=True if a.offline else None)
    case = json.loads((d / "casefile.json").read_text())
    out = []
    for p in case["prs"]:
        out += [to_dict(c) for c in claims_mod.extract(p["number"], p["body"])]
    (d / "claims.json").write_text(json.dumps(out, indent=2))
    print(f"{len(out)} claim candidates")


def cmd_todo(name):
    def f(a):
        raise SystemExit(f"`verdict {name}` not implemented yet. See docs/BUILD_PLAN.md")

    return f


def main():
    ap = argparse.ArgumentParser(prog="verdict")
    sub = ap.add_subparsers(required=True)
    c = sub.add_parser("case")
    c.add_argument("issue", type=int)
    c.add_argument("--offline", action="store_true")
    c.set_defaults(fn=cmd_case)
    k = sub.add_parser("claims")
    k.add_argument("issue", type=int)
    k.add_argument("--offline", action="store_true")
    k.set_defaults(fn=cmd_claims)
    for name in ("evidence", "ledger", "ruling", "serve"):  # TODO phases 3,4,7,6
        s = sub.add_parser(name)
        s.add_argument("issue", type=int, nargs="?")
        s.set_defaults(fn=cmd_todo(name))
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
