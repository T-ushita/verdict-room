from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from . import casefile
from . import claims as claims_mod
from .evidence import check_ci, check_diff, check_policy, check_test_files
from .github import GitHub
from .ledger import merge
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


def _read_agent_json(path: Path, labels: list[str]) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"{path.name}: malformed JSON at line {exc.lineno}, column {exc.colno}"
        ) from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{path.name}: expected a JSON object keyed by claim id")
    for claim_id, value in payload.items():
        if not isinstance(value, dict):
            raise SystemExit(f"{path.name}: entry {claim_id!r} must be a JSON object")
        for label in labels:
            if label not in value:
                raise SystemExit(f"{path.name}: entry {claim_id!r} is missing {label!r}")
    return payload


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
    verdicts = _read_agent_json(
        d / "verdicts.json",
        ["status", "rationale", "judged_by"],
    )
    challenges = _read_agent_json(d / "challenges.json", ["reason", "rebutted"])
    rebuttals = _read_agent_json(d / "rebuttals.json", ["rebuttal"])
    valid_statuses = {status.value for status in Status}
    for filename, payload in (
        ("verdicts.json", verdicts),
        ("rebuttals.json", rebuttals),
    ):
        for claim_id, value in payload.items():
            if claim_id not in claim_ids:
                raise SystemExit(f"{filename}: unknown claim id {claim_id!r}")
            status = value.get("status") or value.get("new_status")
            if status is not None and status not in valid_statuses:
                raise SystemExit(f"{filename}: invalid status {status!r} for {claim_id!r}")
            rationale = (
                value.get("rationale") if filename == "verdicts.json" else value.get("rebuttal")
            )
            if isinstance(rationale, str) and not rationale.strip():
                raise SystemExit(f"{filename}: empty rationale for {claim_id!r}")
    for claim_id, value in challenges.items():
        if claim_id not in claim_ids:
            raise SystemExit(f"challenges.json: unknown claim id {claim_id!r}")
        if not isinstance(value["reason"], str) or not value["reason"].strip():
            raise SystemExit(f"challenges.json: empty rationale for {claim_id!r}")

    rows = merge(claims, evidence, verdicts, challenges, rebuttals)
    (d / "ledger.json").write_text(json.dumps([to_dict(row) for row in rows], indent=2))
    print(f"{'CLAIM':<10} {'PR':<6} {'STATUS':<13} RATIONALE")
    for row in rows:
        print(f"{row.claim_id:<10} {row.pr:<6} {row.status.value:<13} {row.rationale}")
    print(f"{len(rows)} ledger rows")


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
    for name in ("ruling", "serve"):  # TODO phases 7,6
        s = sub.add_parser(name)
        s.add_argument("issue", type=int, nargs="?")
        s.set_defaults(fn=cmd_todo(name))
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
