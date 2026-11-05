from verdict.casefile import build, refs_issue
from verdict.claims import extract, gap_hints
from verdict.github import GitHub
from verdict.redact import redact
from verdict.ruling import gate_open, write_approval


def test_refs_issue():
    assert refs_issue("feat: add Sentry (#820)", "", 820)
    assert refs_issue("x", "Closes #825", 825)
    assert not refs_issue("x", "see also #820 for context", 820)


def test_claims_extract_gap_and_tests():
    body = "Ran 424 tests, all pass.\nThis does not yet provide a working live connection."
    kinds = {c.kind for c in extract(1436, body)}
    assert "tests" in kinds
    assert "self_disclosed_gap" not in kinds
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
    assert not any(c.kind == "self_disclosed_gap" for c in claims)
    hints = gap_hints(body)
    assert "rejects" in hints
    assert "key_never_expires" in hints


def test_gate_requires_everything(tmp_path, monkeypatch):
    monkeypatch.setenv("VERDICT_LIVE_POST", "1")
    assert not gate_open(tmp_path, "d", True)[0]
    write_approval(tmp_path, "d", "maintainer")
    assert gate_open(tmp_path, "d", True)[0]
    assert not gate_open(tmp_path, "d2", True)[0]  # draft changed
    assert not gate_open(tmp_path, "d", False)[0]  # no --live


def test_redact():
    assert "ghp_" not in redact("token ghp_" + "a" * 30)


def test_offline_case_builds_competing_prs():
    case = build(GitHub("sandbox-quantum/switch", offline=True), 825)
    assert case.source == "fixture"
    assert [pr.number for pr in case.prs] == [1432, 1436]
