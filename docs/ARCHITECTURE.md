# Architecture

```
 Maintainer (human)  ──chat──►  Switch room "verdict-<issue>"
                                   │  room instructions + roles + shared case file
        ┌──────────────┬───────────┼───────────────┬──────────────┐
      Clerk         Examiner     Skeptic        Registrar        (human approves)
   (Claude Code)  (Claude Code)  (Codex/other)  (Claude Code)
        │              │            │                │
        └──── all call the same deterministic CLI: `verdict ...` ───┘
                              │
              GitHub REST (read-only)   cases/<id>/*.json  ◄── ui/index.html
```

## Components
| Component | Job | Deterministic? |
|---|---|---|
| `github.py` | Fetch issue, PRs, files, check-runs, comments (read-only) | yes |
| `casefile.py` | Group PRs by linked issue (`Closes #n`, title `(#n)`, body refs) | yes |
| `claims.py` | Pull candidate claims from PR body (counts, "passed", "read-only") | heuristic |
| `evidence/*` | Check a claim against CI, diff, test files, policy flags | yes |
| `ledger.py` | Merge evidence + agent judgments into `ledger.json` | yes |
| `ruling.py` | Draft comments; post only behind the approval gate | yes |
| Agents | Decide which claims matter, interpret evidence, argue, draft tone | LLM |

## Why this split
LLMs are good at reading a PR body and spotting that "424 tests passed" says nothing about
a live connection. They are bad at being the source of truth. Code fetches facts, agents argue about them.

## Data contract (`cases/<id>/`)
- `casefile.json`: issue, acceptance criteria, PR list
- `claims.json`: claims per PR (`id, pr, text, kind, source_quote`)
- `evidence.json`: facts per claim (`claim_id, check, result, link`)
- `ledger.json`: final rows `(claim_id, status, rationale, evidence_links, judged_by)`
- `ruling.draft.md`, `approval.json` (written by human approval step only)

Status values: `VERIFIED | UNVERIFIED | CONTRADICTED | NOT_CHECKABLE`.

## Safety
Read-only token. Dry-run by default. Approval file records who approved and the hash of the draft; changing the draft invalidates approval.
Skeptic never sees the Examiner's conclusions first (blind pass), then compares.
