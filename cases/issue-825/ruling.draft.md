Verdict Room summary for issue #825: Add the PagerDuty connector

The evidence ledger contains the following competing-PR findings:

- PR #1060 - 1060-01 UNVERIFIED - ruff check` clean
- PR #1060 - 1060-02 CONTRADICTED - Least access: PagerDuty has no read-only user key, so `tools: pass_through` (as the loader requires for `api_key`) and the description and skill say plainly that it can write
- PR #1060 - 1060-03 UNVERIFIED - This PR delivers a working integration for the linked issue.
- PR #1391 - 1391-01 UNVERIFIED - This PR delivers a working integration for the linked issue.
- PR #1398 - 1398-01 UNVERIFIED - This PR delivers a working integration for the linked issue.
- PR #1432 - 1432-01 UNVERIFIED - just check` (ruff format + lint) and `just typecheck` (mypy) are clean
- PR #1432 - 1432-02 CONTRADICTED - There's no read-only mode on the server side, so the skill is careful about writes, and the PR doesn't claim one
- PR #1432 - 1432-03 UNVERIFIED - This PR delivers a working integration for the linked issue.
- PR #1436 - 1436-01 UNVERIFIED - | Ruff and Mypy | Passed |
- PR #1436 - 1436-02 CONTRADICTED - | Console lint, typecheck and build | Passed |
- PR #1436 - 1436-03 CONTRADICTED - Dashed arrows describe the intended integration, not a completed end-to-end connection
- PR #1436 - 1436-04 CONTRADICTED - A separately reviewed execution strategy is required before the issue's end-to-end acceptance criteria can be fulfilled
- PR #1436 - 1436-05 UNVERIFIED - Self-disclosed gap: not yet
- PR #1436 - 1436-06 UNVERIFIED - Self-disclosed gap: follow-up
- PR #1436 - 1436-07 UNVERIFIED - Self-disclosed gap: blocked
- PR #1436 - 1436-08 UNVERIFIED - Self-disclosed gap: rejects
- PR #1436 - 1436-09 UNVERIFIED - Self-disclosed gap: key_never_expires
- PR #1611 - 1611-01 UNVERIFIED - pytest core/tests/switch_core/connections core/tests/switch_core/gateway`: all pass except `test_tenant_api_routes::
- PR #1611 - 1611-02 UNVERIFIED - ts` (every catalog slug has a logo and every logo a NOTICE row), and the `connector-apps`, `connectors` and `admin` tests all pass
- PR #1611 - 1611-03 CONTRADICTED - Real read-only level
- PR #1611 - 1611-04 CONTRADICTED - Scoped OAuth gives per-resource scopes, so there is a genuine read-only connection as well as read-write
- PR #1611 - 1611-05 CONTRADICTED - Per-resource scopes with a genuine read-only level
- PR #1611 - 1611-06 CONTRADICTED - This PR delivers a working integration for the linked issue.
- PR #1611 - 1611-07 UNVERIFIED - Self-disclosed gap: key_never_expires


Verdict Room summary for #1060 feat(connections): add the PagerDuty connector (closes #825)

Evidence-ledger findings:
- 1060-01: UNVERIFIED - ruff check` clean
- 1060-02: UNVERIFIED - Least access: PagerDuty has no read-only user key, so `tools: pass_through` (as the loader requires for `api_key`) and the description and skill say plainly that it can write
- 1060-03: UNVERIFIED - This PR delivers a working integration for the linked issue.


Verdict Room summary for #1391 Add the PagerDuty connector (#825)

Evidence-ledger findings:
- 1391-01: UNVERIFIED - This PR delivers a working integration for the linked issue.


Verdict Room summary for #1398 feat(connections): add PagerDuty service connector (#825) #FliptheSwitch

Evidence-ledger findings:
- 1398-01: UNVERIFIED - This PR delivers a working integration for the linked issue.


Verdict Room summary for #1432 Add the PagerDuty connector

Evidence-ledger findings:
- 1432-01: UNVERIFIED - Ran 224 connection tests, all pass
- 1432-02: UNVERIFIED - This PR delivers a working integration for the linked issue.

Please request changes or hold posting until the evidence gaps are resolved.


Verdict Room summary for #1436 feat(connections): add PagerDuty connector (#825)

Evidence-ledger findings:
- 1436-01: UNVERIFIED - Ran 424 connector/broker/catalog tests passed
  Evidence: https://github.com/sandbox-quantum/switch/pull/1436/checks, https://github.com/sandbox-quantum/switch/pull/1436/files, https://github.com/sandbox-quantum/switch/pull/1436/files
- 1436-02: CONTRADICTED - This PR delivers a working integration for the linked issue.
  Evidence: https://github.com/sandbox-quantum/switch/pull/1436/files, https://github.com/sandbox-quantum/switch/pull/1436/files, https://github.com/sandbox-quantum/switch/pull/1436


Verdict Room summary for #1611 feat(connections): add PagerDuty connector (#825)

Evidence-ledger findings:
- 1611-01: UNVERIFIED - pytest core/tests/switch_core/connections core/tests/switch_core/gateway`: all pass except `test_tenant_api_routes::
- 1611-02: UNVERIFIED - ts` (every catalog slug has a logo and every logo a NOTICE row), and the `connector-apps`, `connectors` and `admin` tests all pass
- 1611-03: UNVERIFIED - Real read-only level
- 1611-04: UNVERIFIED - Scoped OAuth gives per-resource scopes, so there is a genuine read-only connection as well as read-write
- 1611-05: UNVERIFIED - Per-resource scopes with a genuine read-only level
- 1611-06: UNVERIFIED - This PR delivers a working integration for the linked issue.
- 1611-07: UNVERIFIED - Self-disclosed gap: key_never_expires
