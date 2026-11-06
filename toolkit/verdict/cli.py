from __future__ import annotations

import argparse
import json
import os
import secrets
from pathlib import Path

from . import casefile
from . import claims as claims_mod
from .evidence import check_ci, check_diff, check_policy, check_test_files
from .github import GitHub
from .ledger import merge, validate_agent_inputs
from .schemas import Claim, Evidence, Status, to_dict

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


def cmd_evidence(a):
    d = _case_dir(a.issue, offline=True if a.offline else None)
    case = json.loads((d / "casefile.json").read_text())
    claims = json.loads((d / "claims.json").read_text())
    gh = GitHub(
        os.environ.get("VERDICT_REPO", "sandbox-quantum/switch"),
        offline=a.offline,
    )
    out = []
    prs = {pr["number"]: pr for pr in case["prs"]}
    for claim_data in claims:
        claim = claims_mod.extract(claim_data["pr"], claim_data.get("source_quote", ""))
        matching = next((item for item in claim if item.id == claim_data["id"]), None)
        if matching is None:
            matching = Claim(
                claim_data["id"],
                claim_data["pr"],
                claim_data["text"],
                claim_data["kind"],
                claim_data["source_quote"],
            )
        pr = prs.get(claim_data["pr"])
        if not pr:
            continue
        pr_url = pr["url"]
        out += [to_dict(item) for item in check_ci(gh, matching, pr["head_sha"], pr_url)]
        out += [to_dict(item) for item in check_diff(gh, matching, pr["number"], pr_url)]
        out += [to_dict(item) for item in check_test_files(gh, matching, pr["number"], pr_url)]
        out += [to_dict(item) for item in check_policy(matching, pr["draft"], pr_url, pr["body"])]
    (d / "evidence.json").write_text(json.dumps(out, indent=2))
    print(f"{len(out)} evidence rows")


def cmd_ledger(a):
    d = _case_dir(a.issue, offline=True if a.offline else None)
    claims_data = json.loads((d / "claims.json").read_text())
    evidence_data = json.loads((d / "evidence.json").read_text())
    claim_ids = {item["id"] for item in claims_data}
    claims = [
        Claim(
            item["id"],
            item["pr"],
            item["text"],
            item["kind"],
            item["source_quote"],
        )
        for item in claims_data
    ]
    evidence = [
        Evidence(
            item["claim_id"],
            item["check"],
            item["result"],
            item["link"],
            Status(item["supports"]) if item.get("supports") else None,
        )
        for item in evidence_data
    ]
    try:
        verdicts, challenges, rebuttals = validate_agent_inputs(d, claim_ids)
    except (TypeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    rows = merge(claims, evidence, verdicts, challenges, rebuttals)
    (d / "ledger.json").write_text(json.dumps([to_dict(row) for row in rows], indent=2))
    print(f"{'CLAIM':<10} {'PR':<6} {'STATUS':<13} RATIONALE")
    for row in rows:
        print(f"{row.claim_id:<10} {row.pr:<6} {row.status.value:<13} {row.rationale}")
    print(f"{len(rows)} ledger rows")


def cmd_serve(a):
    from .server import Handler, VerdictServer

    token = os.environ.get("VERDICT_SESSION_TOKEN") or secrets.token_urlsafe(32)
    server = VerdictServer(("127.0.0.1", a.port), Handler, token)
    print(f"Verdict Room: http://127.0.0.1:{a.port}")
    print("Session token loaded into the local UI; do not share or commit it.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


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
    e = sub.add_parser("evidence")
    e.add_argument("issue", type=int)
    e.add_argument("--offline", action="store_true")
    e.set_defaults(fn=cmd_evidence)
    ledger = sub.add_parser("ledger")
    ledger.add_argument("issue", type=int)
    ledger.add_argument("--offline", action="store_true")
    ledger.set_defaults(fn=cmd_ledger)
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8787)
    serve.set_defaults(fn=cmd_serve)
    for name in ("ruling",):  # TODO phase 7
        s = sub.add_parser(name)
        s.add_argument("issue", type=int, nargs="?")
        s.set_defaults(fn=cmd_todo(name))
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
