# Instructions for the coding agent

You are building **Verdict Room**. Read `README.md`, `docs/ARCHITECTURE.md`, `docs/BUILD_PLAN.md` first.
Work through `docs/BUILD_PLAN.md` phase by phase. Do not skip ahead.

## Rules
- Inspect before changing. Smallest complete change. Run `just test` and `just check` before saying a phase is done.
- Python 3.11+, standard library first. Allowed deps: `pytest`, `ruff`. Ask before adding any other.
- Never claim something works without running it. State what is unverified.
- No secrets in git. `.env` is ignored. Never print tokens. Redact in logs (`verdict/redact.py`).
- **No GitHub writes** except in `verdict/ruling.py::post()`, and only when ALL are true:
  approval file exists, `VERDICT_LIVE_POST=1`, `--live` flag passed. Otherwise print the dry-run.
- Evidence checks must be deterministic code. LLM agents judge *meaning*; code establishes *facts*.
- Every ledger row must carry an evidence link (URL or file:line). No link, status is `UNVERIFIED`.
- Mark anything mocked or recorded in the UI and README. Do not hide it.

## Phase 0 is mandatory: Switch discovery
Before writing room files, confirm against Switch docs how to: define room instructions/roles,
add a second agent, share room documents, and mention agents.
Docs MCP: `claude mcp add switch-docs --transport http https://docs.switchagents.ai/mcp`
Write findings to `docs/SWITCH_NOTES.md` (what is confirmed vs guessed). Adjust `room/` accordingly.

## Layout
- `toolkit/verdict/` the CLI agents call as tools (fetch, claims, evidence, ledger, ruling)
- `room/` room instructions and per-agent role prompts (paste or import into Switch)
- `ui/index.html` single-file case board, reads `cases/<id>/ledger.json`
- `fixtures/` recorded GitHub responses for offline demo and tests
