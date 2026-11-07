import json
import threading
import urllib.error
import urllib.request

from verdict import server as server_module
from verdict.casefile import build, refs_issue
from verdict.claims import extract, gap_hints
from verdict.evidence.ci import check_ci
from verdict.evidence.diff import check_diff
from verdict.evidence.policy import check_policy
from verdict.github import GitHub
from verdict.ledger import merge, validate_agent_inputs
from verdict.redact import redact
from verdict.ruling import (
    draft_hash,
    gate_open,
    generate_drafts,
    normalize_draft_text,
    save_issue_approval,
    save_pr_approval,
    write_approval,
)
from verdict.scanner import fingerprint, issue_numbers, pr_status, scan
from verdict.schemas import Claim, Evidence, Status


def test_mojibake_and_unicode_dashes_are_normalized():
    assert server_module.clean_text("Ran tests â€” all pass") == "Ran tests - all pass"
    assert server_module.clean_payload({"text": "Evidence â€“ check"}) == {
        "text": "Evidence - check"
    }
    assert server_module.clean_text("Working — now") == "Working - now"


def test_refs_issue():
    assert refs_issue("feat: add Sentry (#820)", "", 820)
    assert refs_issue("x", "Closes #825", 825)
    assert not refs_issue("x", "see also #820 for context", 820)


def test_claims_extract_gap_and_tests():
    body = "Ran 424 tests, all pass.\nThis does not yet provide a working live connection."
    kinds = {c.kind for c in extract(1436, body)}
    assert "tests" in kinds
    assert "self_disclosed_gap" in kinds
    assert "e2e" not in kinds


def test_implicit_e2e_and_gap_hints():
    body = (
        "Ran 424 connector/broker/catalog tests passed.\n"
        "The broker rejects non-expiring API keys (key_never_expires).\n"
        "No agent grant is available yet.\n"
        "Closes #825"
    )
    claims = extract(1436, body)
    assert any(c.kind == "e2e" and c.source_quote.startswith("Implicit") for c in claims)
    assert any(c.kind == "self_disclosed_gap" for c in claims)
    hints = gap_hints(body)
    assert "rejects" in hints
    assert "key_never_expires" in hints


def test_gate_requires_everything(tmp_path, monkeypatch):
    monkeypatch.setenv("VERDICT_LIVE_POST", "1")
    monkeypatch.setenv("VERDICT_REPO", "sandbox-quantum/switch")
    monkeypatch.setenv("VERDICT_POST_REPO", "user/switch-fork")
    monkeypatch.setenv("VERDICT_POST_ISSUE", "999")
    assert not gate_open(tmp_path, "d", True)[0]
    write_approval(tmp_path, "d", "maintainer")
    save_issue_approval(tmp_path, "d", "maintainer", "approved")
    assert gate_open(tmp_path, "d", True)[0]
    assert not gate_open(tmp_path, "d2", True)[0]  # draft changed
    assert not gate_open(tmp_path, "d", False)[0]  # no --live


def test_ui_pr_approval_and_saved_draft_share_gate_hash(tmp_path, monkeypatch):
    monkeypatch.setenv("VERDICT_LIVE_POST", "1")
    monkeypatch.setenv("VERDICT_REPO", "sandbox-quantum/switch")
    monkeypatch.setenv("VERDICT_POST_REPO", "user/switch-fork")
    monkeypatch.setenv("VERDICT_POST_ISSUE", "999")

    textarea = "Verdict Room summary\r\n\r\nEvidence-ledger findings:\n- 825-01: VERIFIED\n"
    approval = save_pr_approval(
        tmp_path,
        1432,
        textarea,
        "maintainer",
        "approved",
        "Looks complete.",
    )

    saved = (tmp_path / "drafts" / "1432.md").read_text(encoding="utf-8")
    save_issue_approval(tmp_path, saved, "maintainer", "approved")
    assert normalize_draft_text(saved) == normalize_draft_text(textarea)
    assert approval["draft_hash"] == draft_hash(saved)
    assert gate_open(tmp_path, saved, True)[0]


def test_redact():
    assert "ghp_" not in redact("token ghp_" + "a" * 30)


def test_offline_case_builds_competing_prs():
    case = build(GitHub("sandbox-quantum/switch", offline=True), 825)
    assert case.source == "fixture"
    assert [pr.number for pr in case.prs] == [1432, 1436]


class FakeGitHub:
    def __init__(self, check_runs=None, files=None):
        self.check_runs_data = check_runs or {"check_runs": []}
        self.files = files or []

    def check_runs(self, sha):
        return self.check_runs_data

    def pr_files(self, pr_number):
        return self.files


def test_ci_failure_is_contradicted():
    claim = Claim("1436-01", 1436, "tests pass", "tests", "tests pass")
    rows = check_ci(
        FakeGitHub({"check_runs": [{"conclusion": "failure"}]}),
        claim,
        "sha",
        "https://example/pr/1436",
    )
    assert rows[0].supports == Status.CONTRADICTED


def test_ci_action_required_is_unverified():
    claim = Claim("1436-01", 1436, "tests pass", "tests", "tests pass")
    rows = check_ci(
        FakeGitHub({"check_runs": [{"conclusion": "action_required"}]}),
        claim,
        "sha",
        "https://example/pr/1436",
    )
    assert rows[0].supports == Status.UNVERIFIED


def test_contradictory_test_errors_override_all_pass_claim():
    claim = Claim("1432-01", 1432, "224 tests pass", "tests", "224 tests pass")
    rows = check_policy(
        claim,
        False,
        "https://example/pr/1432",
        "224 passed and 131 errored.",
    )
    assert rows[0].supports == Status.CONTRADICTED


def test_gap_policy_contradicts_e2e():
    claim = Claim("1436-02", 1436, "working integration", "e2e", "working integration")
    rows = check_policy(
        claim,
        False,
        "https://example/pr/1436",
        "The broker rejects key_never_expires; no agent grant is available yet",
    )
    assert rows[0].supports == Status.CONTRADICTED


def test_diff_flags_missing_integration_path():
    claim = Claim("1432-02", 1432, "working integration", "e2e", "working integration")
    rows = check_diff(
        FakeGitHub(files=[{"filename": "toolkit/test_core.py", "patch": ""}]),
        claim,
        1432,
        "https://example/pr/1432",
    )
    assert rows[0].supports == Status.UNVERIFIED


def test_diff_integration_path_is_weak_support():
    claim = Claim("1436-02", 1436, "working integration", "e2e", "working integration")
    rows = check_diff(
        FakeGitHub(files=[{"filename": "tests/e2e/connector_test.py", "patch": ""}]),
        claim,
        1436,
        "https://example/pr/1436",
    )
    assert rows[0].supports == Status.UNVERIFIED
    assert "integration/e2e test path present" in rows[0].result


def test_claims_extract_errored_tests_and_verified_via():
    body = "131 connection tests errored in Docker.\nIdentity was verified via /users/me."
    claims = extract(1432, body)
    assert any(c.kind == "tests" and "131" in c.text for c in claims)
    assert any(c.kind == "e2e" and "/users/me" in c.text for c in claims)


def test_ledger_code_contradiction_overrides_unverified():
    claim = Claim("1436-02", 1436, "working integration", "e2e", "working integration")
    evidence = [
        Evidence(
            claim.id,
            "policy",
            "PR body contains gap language",
            "https://example/pr/1436",
            Status.CONTRADICTED,
        )
    ]
    rows = merge(
        [claim],
        evidence,
        {claim.id: {"status": "UNVERIFIED", "rationale": "uncertain", "judged_by": "Examiner"}},
        {},
    )
    assert rows[0].status == Status.CONTRADICTED


def test_ledger_code_contradiction_overrides_rebuttal():
    claim = Claim("1436-02", 1436, "working integration", "e2e", "working integration")
    evidence = [
        Evidence(
            claim.id,
            "policy",
            "PR body contains gap language",
            "https://example/pr/1436",
            Status.CONTRADICTED,
        )
    ]
    rows = merge(
        [claim],
        evidence,
        {"1436-02": {"status": "UNVERIFIED", "rationale": "uncertain"}},
        {},
        {"1436-02": {"rebuttal": "new evidence", "new_status": "VERIFIED"}},
    )
    assert rows[0].status == Status.CONTRADICTED


def test_ledger_no_evidence_forces_unverified():
    claim = Claim("1432-01", 1432, "tests pass", "tests", "tests pass")
    rows = merge([claim], [], {}, {})
    assert rows[0].status == Status.UNVERIFIED
    assert rows[0].evidence_links == []


def test_ledger_exposes_challenge_and_rebuttal():
    claim = Claim("1436-02", 1436, "working integration", "e2e", "working integration")
    rows = merge(
        [claim],
        [],
        {
            claim.id: {
                "status": "UNVERIFIED",
                "rationale": "Not enough live evidence",
                "judged_by": "red-examiner",
            }
        },
        {claim.id: {"reason": "Missing acceptance criteria", "rebutted": False}},
        {claim.id: {"rebuttal": "Issue does not require live access"}},
    )
    assert rows[0].challenged is True
    assert rows[0].challenge_reason == "Missing acceptance criteria"
    assert rows[0].rebuttal == "Issue does not require live access"


def test_gate_rejects_upstream_posting(tmp_path, monkeypatch):
    monkeypatch.setenv("VERDICT_LIVE_POST", "1")
    monkeypatch.setenv("VERDICT_REPO", "sandbox-quantum/switch")
    monkeypatch.setenv("VERDICT_POST_REPO", "sandbox-quantum/switch")
    monkeypatch.setenv("VERDICT_POST_ISSUE", "999")
    write_approval(tmp_path, "d", "maintainer")
    ok, reason = gate_open(tmp_path, "d", True)
    assert not ok
    assert "upstream" in reason


def test_generate_drafts(tmp_path):
    (tmp_path / "casefile.json").write_text(
        json.dumps(
            {
                "issue": 825,
                "issue_title": "Test issue",
                "prs": [{"number": 1432, "title": "First PR"}],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "ledger.json").write_text(
        json.dumps(
            [
                {
                    "claim_id": "1432-01",
                    "pr": 1432,
                    "claim": "Tests pass",
                    "status": "UNVERIFIED",
                    "evidence_links": ["https://example.com/checks"],
                }
            ]
        ),
        encoding="utf-8",
    )
    generated = generate_drafts(tmp_path)
    assert "1432-01: UNVERIFIED" in generated["1432"]
    assert "issue #825" in generated["issue"]
    assert (tmp_path / "ruling.draft.md").exists()


def test_scanner_detects_new_then_unchanged_only(tmp_path):
    class FakeGitHub:
        def list_prs(self, state="all", stop_before="", per_page=100):
            return [
                {
                    "number": 1432,
                    "title": "Add connection",
                    "body": "No issue reference",
                    "state": "open",
                    "draft": False,
                    "merged": False,
                    "updated_at": "2026-11-07T00:00:00Z",
                    "head": {"sha": "abc123"},
                    "html_url": "https://example.com/pr/1432",
                }
            ]

    first = scan(FakeGitHub(), tmp_path, "sandbox-quantum/switch", now="2026-11-07T01:00:00Z")
    assert first["changed_count"] == 1
    assert first["changed"][0]["change"] == "NEW"

    second = scan(FakeGitHub(), tmp_path, "sandbox-quantum/switch", now="2026-11-07T02:00:00Z")
    assert second["changed_count"] == 0
    assert second["unchanged_count"] == 1


def test_scanner_pr_status_issue_reference_and_fingerprint():
    pr = {
        "number": 1436,
        "title": "Fix connector (#825)",
        "body": "Closes #825",
        "state": "open",
        "draft": True,
        "merged": False,
        "updated_at": "2026-11-07T00:00:00Z",
        "head": {"sha": "def456"},
    }
    assert issue_numbers(pr) == [825]
    assert pr_status(pr) == "BLOCKED_DRAFT"
    assert fingerprint(pr).startswith("def456|2026-11-07T00:00:00Z")


def test_strict_ledger_validation_rejects_bad_status(tmp_path):
    (tmp_path / "claims.json").write_text("[]")
    (tmp_path / "verdicts.json").write_text(
        '{"1436-02":{"status":"MAYBE","rationale":"uncertain","judged_by":"Examiner"}}'
    )
    try:
        validate_agent_inputs(tmp_path, {"1436-02"})
    except ValueError as exc:
        assert "invalid status" in str(exc)
    else:
        raise AssertionError("invalid verdict status should fail")


def test_agent_json_accepts_utf8_bom(tmp_path):
    (tmp_path / "verdicts.json").write_text(
        "\ufeff"
        + '{"1436-02":{"status":"UNVERIFIED","rationale":"uncertain","judged_by":"Examiner"}}',
        encoding="utf-8",
    )
    verdicts, _, _ = validate_agent_inputs(tmp_path, {"1436-02"})
    assert verdicts["1436-02"]["status"] == "UNVERIFIED"


def test_strict_ledger_validation_rejects_malformed_json(tmp_path):
    (tmp_path / "challenges.json").write_text("{bad")
    try:
        validate_agent_inputs(tmp_path, {"1436-02"})
    except ValueError as exc:
        assert "malformed JSON" in str(exc)
    else:
        raise AssertionError("malformed JSON should fail")


def test_localhost_server_case_api_and_origin_guard(tmp_path, monkeypatch):
    case_dir = tmp_path / "cases" / "issue-825"
    case_dir.mkdir(parents=True)
    (case_dir / "casefile.json").write_text(
        json.dumps(
            {
                "issue": 825,
                "issue_title": "Test case",
                "issue_body": "",
                "prs": [],
                "source": "fixture",
            }
        )
    )
    (case_dir / "ledger.json").write_text("[]")
    ui = tmp_path / "index.html"
    ui.write_text("<script>const token = __VERDICT_SESSION_TOKEN__; </script>")
    monkeypatch.setattr(server_module, "CASES", tmp_path / "cases")
    monkeypatch.setattr(server_module, "UI", ui)

    server = server_module.VerdictServer(("127.0.0.1", 0), server_module.Handler, "test-token")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    base = f"http://127.0.0.1:{port}"
    try:
        with urllib.request.urlopen(base + "/api/cases", timeout=2) as response:
            assert json.load(response)["cases"][0]["issue"] == 825

        request = urllib.request.Request(
            base + "/api/cases/825/override",
            data=json.dumps(
                {
                    "claim_id": "1436-02",
                    "status": "VERIFIED",
                    "note": "maintainer override",
                    "approver": "Test User",
                }
            ).encode(),
            headers={
                "Content-Type": "application/json",
                "X-Verdict-Token": "wrong",
                "Origin": base,
                "Host": f"127.0.0.1:{port}",
            },
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=2)
        except urllib.error.HTTPError as exc:
            assert exc.code == 401
        else:
            raise AssertionError("wrong session token should be rejected")
    finally:
        server.shutdown()
        server.server_close()


def test_localhost_override_updates_persisted_ledger(tmp_path, monkeypatch):
    case_dir = tmp_path / "cases" / "issue-825"
    case_dir.mkdir(parents=True)
    (case_dir / "casefile.json").write_text(
        json.dumps(
            {"issue": 825, "issue_title": "Test", "issue_body": "", "prs": [], "source": "fixture"}
        )
    )
    (case_dir / "ledger.json").write_text(
        json.dumps(
            [{"claim_id": "1432-02", "status": "UNVERIFIED", "rationale": "", "judged_by": "code"}]
        )
    )
    ui = tmp_path / "index.html"
    ui.write_text("<script>const token = __VERDICT_SESSION_TOKEN__; </script>")
    monkeypatch.setattr(server_module, "CASES", tmp_path / "cases")
    monkeypatch.setattr(server_module, "UI", ui)

    server = server_module.VerdictServer(("127.0.0.1", 0), server_module.Handler, "test-token")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        payload = json.dumps(
            {
                "claim_id": "1432-02",
                "status": "CONTRADICTED",
                "note": "Maintainer found contradiction",
                "approver": "Tushita",
            }
        ).encode()
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/cases/825/override",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Verdict-Token": "test-token",
                "Origin": f"http://127.0.0.1:{port}",
                "Host": f"127.0.0.1:{port}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            assert response.status == 200
        ledger = json.loads((case_dir / "ledger.json").read_text())
        assert ledger[0]["status"] == "CONTRADICTED"
        assert ledger[0]["rationale"] == "Maintainer found contradiction"
        assert ledger[0]["judged_by"] == "Tushita"
    finally:
        server.shutdown()
        server.server_close()
