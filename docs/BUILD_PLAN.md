# Build plan (≈ 2 days). Each phase ends with a runnable check.

## Phase 0 — Switch discovery (1h)
Confirm room instructions/roles, second agent, shared docs, mentions. Write `docs/SWITCH_NOTES.md`.
Get ONE agent answering in a room. Done when: a message in the room gets a reply.

## Phase 1 — Case file (2h)
Implement `github.py` (urllib, token from env, ETag-free, 1 retry), `casefile.py`.
Record fixtures: `scripts/record_fixtures.sh` for issues 820, 825 and their PRs.
Done when: `verdict case 820 --offline` writes `casefile.json` listing the competing PRs.

## Phase 2 — Claims (1.5h)
`claims.py`: regex extraction (test counts, "tests pass", "lint/mypy", "read-only", "no breaking change",
"end-to-end", "works with X"). Also extract the PR's own "not yet / follow-up / draft / outstanding" statements as
`kind=self_disclosed_gap`. These matter most.
Done when: unit tests extract claims from fixture PR bodies.

## Phase 3 — Evidence checks (3h)
Implement in `evidence/`:
- `ci.py`: check-run conclusions for head SHA. Claim "tests pass" vs actual runs.
- `diff.py`: files changed by layer (core/gateway/console), test files added, docs touched.
- `tests.py`: do added test files reference the new code? count test functions added.
- `policy.py`: flags: write-capable but described read-only; secrets patterns in diff; "never expires" credential policy mentions; draft state.
Done when: each claim in fixtures gets >=1 evidence row or `NOT_CHECKABLE`.

## Phase 4 — Ledger + Skeptic loop (2h)
`ledger.py` merges agent judgments (`verdicts.json` written by Examiner, `challenges.json` by Skeptic).
Rule: a row the Skeptic challenged and Examiner did not rebut drops to `UNVERIFIED`.
Done when: `verdict ledger 820` prints a table and writes `ledger.json`.

## Phase 5 — Room roles (2h)
Finalize `room/instructions.md` and `room/roles/*.md` per Phase 0 findings. Run the full flow in a real room on case 820.

## Phase 6 — UI (3h)
`ui/index.html` is scaffolded with fixture data. Wire to `cases/<id>/ledger.json` via `verdict serve`.
Add the approval buttons that write `approval.json` (localhost only).

## Phase 7 — Ruling + gate (1.5h)
`ruling.py`: draft per-PR comments + one summary comment on the issue. `post()` behind the gate. Tests for the gate.
Demo posts to a sandbox fork repo, never the live Switch repo.

## Phase 8 — Submission (3h)
README honest limitations, 3-min demo video (`docs/DEMO_SCRIPT.md`), clean-clone test, blog post (side track).

## Cut line if time runs out
Keep: Phases 0-4, 6 (read-only UI), room flow. Cut: live posting, second case, Skeptic blind pass.
