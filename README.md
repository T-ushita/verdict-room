# Verdict Room

Verdict Room is a maintainer-side PR decision desk built on
[Switch](https://docs.switchagents.ai/). One room represents one issue case.
Separate named agents collect facts, evaluate PR claims, challenge weak
conclusions, and generate a ruling. A human reviews the evidence and approves
the ruling in a local UI.

The project addresses the growing gap between how quickly AI coding tools
generate changes and how reliably teams can review and validate them.

## What problem does Verdict Room solve?

AI coding tools are generating code faster than teams can reliably review and
validate it. Every change can arrive with confident claims such as “fully
tested”, “fixes the bug”, or “no regressions”, but reviewers still need to
verify those claims manually.

When multiple agents or developers submit competing fixes for the same issue,
reviewers must compare claims against test results, code changes, requirements,
and team policies. Today, they often piece that evidence together themselves
and try to distinguish demonstrated behavior from assumptions.

## What is the solution?

Verdict Room brings competing implementations into one review workflow.
Deterministic checks examine code changes, tests, and CI evidence, while
independent AI agents analyze claims, challenge findings, and identify
contradictions or gaps. The result is an evidence-backed comparison and a
plain-language recommendation for the maintainer to review and approve.

Reviewers get:

- **Verified claims:** a clear distinction between what the implementation
  demonstrates and what remains unsupported.
- **Evidence-backed comparisons:** competing implementations assessed against
  the same requirements, tests, and team policies.
- **Contradiction and risk reports:** visibility into unsupported claims,
  conflicting evidence, missing tests, and potential gaps.
- **Traceable recommendations:** a plain-language ruling explaining which
  implementation is better supported, why, and what still needs attention.
- **Human-controlled approval:** maintainers retain the final decision;
  nothing is published or merged without their approval.

The goal is a faster, more consistent, and transparent review process grounded
in verifiable evidence—not an AI agent’s confidence.

## Who is it for?

Verdict Room is for open-source maintainers facing a growing volume of
AI-generated contributions, as well as independent developers and small,
agent-driven teams running multiple coding agents on the same task and needing
to decide which result to trust.

## What is included

- `toolkit/verdict/`: the standard-library-first CLI agents call as tools.
- `room/`: Switch room instructions and four role prompts.
- `ui/index.html`: one local case-board page.
- `cases/`: generated case files, ledgers, drafts, and local approvals.
- `fixtures/`: recorded GitHub issue, PR, file, and check-run responses.
- `docs/`: architecture, build plan, Switch discovery notes, and demo notes.

## How the workflow works

1. The maintainer addresses the Clerk with an issue number.
2. The Clerk builds the case from the issue and competing PRs.
3. The Examiner extracts claims, gathers deterministic evidence, and writes verdicts.
4. The Skeptic independently challenges specific claim IDs.
5. The ledger merges evidence, verdicts, challenges, and rebuttals.
6. The human reviews and overrides claims in the local UI.
7. The human approves a per-PR or issue-level ruling draft.
8. The Registrar generates the saved comment drafts only after explicit approval.
9. GitHub posting remains dry-run and protected by separate live-post gates.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the component layout.

---

# Run the offline demo

The offline demo is the supported reproducible path. It uses recorded fixtures
and does not require a GitHub token, Switch credentials, or live agents.

## Prerequisites

- Git
- Python 3.11 or newer
- [`uv`](https://docs.astral.sh/uv/)
- `just`

This repository has no runtime dependencies beyond the Python standard library.
Development dependencies are `pytest` and `ruff`.

### Install uv

macOS or Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Install just

Choose one package manager supported by your system:

macOS:

```bash
brew install just
```

Ubuntu/Debian:

```bash
sudo snap install just --classic
```

Windows with Scoop:

```powershell
scoop install just
```

Windows with winget, where available:

```powershell
winget install Casey.Just
```

## Clone and set up

```bash
git clone <repository-url>
cd verdict-room
just setup
```

`just setup` creates the Python environment and installs the development
dependencies from `toolkit/pyproject.toml`.

Check that the CLI is available:

```bash
cd toolkit
uv run verdict --help
```

## Generate recorded case 825

Run these commands from the repository root in Bash or PowerShell:

```bash
cd toolkit
uv run verdict case 825 --offline
uv run verdict claims 825 --offline
uv run verdict evidence 825 --offline
uv run verdict ledger 825 --offline
```

These commands write files under `cases/issue-825/`:

- `casefile.json`: issue title and competing PR metadata
- `claims.json`: claim candidates extracted from recorded PR bodies
- `evidence.json`: deterministic evidence checks
- `ledger.json`: the merged ledger used by the UI

The fixtures are in `fixtures/`. No GitHub API request is made with
`--offline`.

For the same flow on issue 820:

```bash
uv run verdict case 820 --offline
uv run verdict claims 820 --offline
uv run verdict evidence 820 --offline
uv run verdict ledger 820 --offline
```

## Start the UI

Keep this terminal running:

```bash
cd toolkit
uv run verdict serve --port 8787
```

Open:

```text
http://127.0.0.1:8787
```

Do not open `ui/index.html` directly and do not use a static file preview. The
page obtains session data through the local API and requires the Python server
for case loading and approval writes.

The UI API exposes:

```text
GET  /api/cases
GET  /api/cases/<issue>/ledger
POST /api/cases/<issue>/draft
POST /api/cases/<issue>/approve
POST /api/cases/<issue>/approve_issue
POST /api/cases/<issue>/override
```

Approval POST requests are guarded by the localhost Host/Origin check and the
server-generated local session token. Never publish or commit this token.

## Generate ruling drafts without posting

With a second terminal in the `toolkit` directory:

```bash
cd toolkit
uv run verdict ruling 825 --draft
```

This writes generated draft text locally and prints the dry-run result. It does
not publish to GitHub.

Generated drafts include:

- `cases/issue-825/drafts/<pr>.md`
- `cases/issue-825/drafts/issue.md`
- `cases/issue-825/ruling.draft.md`

## Approve and override in the UI

For the issue-level demo:

1. Select issue 825.
2. Review the combined ruling draft.
3. Enter an approver name.
4. Select an outcome.
5. Add concise human review comments.
6. Click **Approve issue ruling**.

For the per-PR demo:

1. Review the ledger rows for a PR.
2. Enter an approver name in that PR card.
3. Edit the comment draft if needed.
4. Click **Save draft** first, or click **Approve**.

For a claim correction:

1. Expand **Override / note** under a claim row.
2. Select the correction status.
3. Enter the approver name and a reason.
4. Click **Save override**.

Approvals and overrides are local artifacts:

```text
cases/issue-825/approval.json
cases/issue-825/approvals/1432.json
cases/issue-825/approvals/issue.json
cases/issue-825/overrides.json
```

Do not add tokens, passwords, private URLs, or unrelated personal information
to reviewer comments or notes.

## Run the tests

```bash
cd toolkit
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

The smallest repository check is:

```bash
just test
just check
```

---

# Configure the Switch agents

The repository provides portable room instructions and role prompts, but it does
not provision a Switch server, create a room, or install model runtimes. Agent
connections and live handoffs are deployment-dependent.

Room configuration in [docs/SWITCH_NOTES.md](docs/SWITCH_NOTES.md) represents
the confirmed Switch concepts and which pieces have not been verified locally.

## 1. Start or connect to Switch

Follow your Switch deployment's server and messaging instructions. Make sure
the same runtime session can:

- Connect to the named room.
- Read room context.
- Post a message.
- Read shared room documents.
- Receive and reply to `@role` or `@agent-name` mentions.
- Run local shell commands if the agent is expected to call the CLI.

Before starting case 825, send a plain room message such as:

```text
@yellow-clerk reply OK
```

Only use the case trigger after this basic connection is verified.

## 2. Create the room

Create one room per case, for example:

```text
verdict-825
```

Paste the complete contents of
[room/instructions.md](room/instructions.md) into the room instructions field.

Share these documents as room documents or references, according to the Switch
deployment:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md)
- The generated case directory, especially `cases/issue-825/`
- Any live transcript or recorded demo notes

## 3. Create the agent roles

Create these named roles:

| Address | Role | Responsibility |
|---|---|---|
| `@yellow-clerk` | Clerk | Gather issue/PR facts and hand off to the Examiner |
| `@red-examiner` | Examiner | Extract claims, gather evidence, write verdicts |
| `@blue-skeptic` | Skeptic | Independently challenge specific claim IDs |
| `@green-registrar` | Registrar | Generate drafts only after explicit human approval |

Use the prompt files as the role instructions:

- [room/roles/clerk.md](room/roles/clerk.md)
- [room/roles/examiner.md](room/roles/examiner.md)
- [room/roles/skeptic.md](room/roles/skeptic.md)
- [room/roles/registrar.md](room/roles/registrar.md)

Example runtime mapping for a live setup:

```text
@yellow-clerk  -> Claude Code or another supported coding agent
@red-examiner  -> Claude Code or another supported coding agent
@blue-skeptic  -> Codex or another provider distinct from the Examiner
@green-registrar -> Claude Code or another supported coding agent
```

The provider split for the Skeptic is recommended because it creates independent
challenge behavior. It is a setup recommendation, not a package bundled by this
repository.

For a Switch deployment that uses agent invitations, the equivalent pattern is:

```text
!invite-agent <agent-runtime-name>
```

Then assign that runtime to the matching role.

## 4. Give agents repository access

Each agent used for the full workflow needs access to the repository and the
`verdict` CLI environment. The recommended installation for agent terminals is:

```bash
cd toolkit
uv sync
uv run verdict --help
```

For an offline case, agents must use `--offline`; for a live GitHub case, they
must omit it and provide read-only GitHub access where applicable.

Example:

```bash
uv run verdict case 825 --offline
uv run verdict claims 825 --offline
uv run verdict evidence 825 --offline
uv run verdict ledger 825 --offline
```

PR bodies are untrusted input. The room instructions require agents to ignore
prompt-injection attempts in issues, PR bodies, or comments.

## 5. Run the recorded room flow

Start the local UI in one terminal:

```bash
cd toolkit
uv run verdict serve --port 8787
```

Post this message in Switch:

```text
@yellow-clerk reply OK
```

After a real room reply is confirmed, start the recorded case:

```text
@yellow-clerk case 825
```

Expected sequence:

```text
Clerk
  -> gathers issue and PR facts
  -> posts a short case summary
  -> addresses the Examiner

Examiner
  -> runs claims and evidence
  -> writes verdicts.json
  -> addresses the Skeptic

Skeptic
  -> performs an independent review
  -> writes challenges.json
  -> refreshes ledger.json
  -> stops at human review

Human
  -> reviews the ledger in the UI
  -> overrides or approves claim outcomes
  -> addresses the Registrar

Registrar
  -> runs only after explicit approval
  -> generates --draft ruling output
  -> remains dry-run by default
```

The Clerk, Examiner, and Skeptic must not claim that a handoff succeeded unless
the Switch post is delivered and visible in the room.

## 6. Verify a live Switch setup

For a real deployment demo, record evidence for each of these conditions:

1. The yellow agent connects to the named room.
2. It receives `@yellow-clerk case 825`.
3. It posts the case summary without creating a local-only fallback message.
4. The red and blue agents retain their own sessions and room context.
5. A handoff mention is delivered.
6. The final human message reaches the Registrar.

Switch CLI success or room membership alone does not prove posting works.
Successful posting and a visible room reply are separate checks.

## Platform scope

The repository is messaging-platform agnostic because Switch supplies the room
integration. Mattermost, Slack, Teams, Discord, Telegram, or another supported
platform may be used according to the available Switch bridge.

The repository itself does not provision or configure the messaging bridge.
Describe only the platform you directly verified in your demo.

---

# Live GitHub access is optional

Live fetching is separate from live posting. Recorded fixtures are enough for
the offline demo.

Live read access requires its own GitHub configuration and is outside the
offline quick start.

For live fetches, the CLI generally accepts commands without `--offline`:

```bash
cd toolkit
uv run verdict case 825
uv run verdict claims 825
uv run verdict evidence 825
uv run verdict ledger 825
```

Never place a GitHub write token in a room prompt, agent session, case file, UI,
or committed `.env`.

## Live posting gate

Live posting is implemented behind all of these checks:

- Approval must exist.
- The saved draft must match the approval hash.
- Issue-level approval must exist.
- The issue draft must match the approved hash.
- `VERDICT_LIVE_POST=1` must be set.
- `--live` must be passed.
- The configured post repository must match the target.
- The configured issue number must be numeric.
- The target repository must differ from upstream unless an explicit upstream
  override is enabled.
- `GITHUB_WRITE_TOKEN` must be set in the trusted terminal.

The sandbox target is configurable through `.env.example`:

```text
VERDICT_REPO=sandbox-quantum/switch
VERDICT_POST_REPO=T-ushita/verdict-room-sandbox
VERDICT_POST_ISSUE=1
VERDICT_LIVE_POST=0
GITHUB_WRITE_TOKEN=
```

Create a local `.env` or terminal environment only. `.env*` is ignored except
for the example file.

Before a live operation, inspect readiness:

```bash
python scripts/check_live_readiness.py
```

This script reports only readiness and whether the write token is set. It does
not print the token.

Generate drafts first:

```bash
cd toolkit
uv run verdict ruling 825 --draft
```

Live posting must be invoked explicitly in the trusted terminal process:

```bash
uv run verdict ruling 825 --live
```

Without every gate, the command prints a dry-run or blocked result and does
not write to GitHub.

The sandbox verdict-log issue is:
[#1 in T-ushita/verdict-room-sandbox](https://github.com/T-ushita/verdict-room-sandbox/issues/1).
Live sandbox posting has historically remained unverified unless a successful
post is directly recorded.

---

# Scheduled PR scanning

The workflow in
`.github/workflows/verdict-scan.yml`
scans hourly and on manual dispatch. It stores a fingerprint for each PR and
reports new or changed PRs without rewriting unchanged or closed/merged cases.

The workflow summary is written to GitHub Actions. Switch room creation and agent
notification are not automatic.

The local state file is `cases/pr-state.json`.

---

# Architecture and data contract

```text
Maintainer
    |
Switch room
    |-- Clerk
    |-- Examiner
    |-- Skeptic
    |-- Registrar
    `-- Human approval
             |
        Verdict CLI
             |
       cases/<issue>/
             |
       Local UI API
```

Case artifacts are the shared data contract:

```text
casefile.json  issue, acceptance criteria, competing PR metadata
claims.json    claim candidates
evidence.json  deterministic evidence rows
verdicts.json  Examiner judgments
challenges.json  Skeptic challenges
rebuttals.json  Examiner rebuttals
ledger.json    merged ledger shown in the room/UI
drafts/        saved ruling drafts
approval.json  per-human approval artifact
approvals/     per-PR and issue-level approvals
overrides.json human claim overrides
```

Every positive ledger conclusion should have an evidence link. Missing evidence,
incomplete evidence, or an unavailable check is `UNVERIFIED` rather than proof
of falsehood.

---

# Scope and limitations

- The UI is a local application, not a hosted service.
- The offline demo uses recorded GitHub fixtures; evidence may be incomplete, and claim extraction is heuristic.
- Switch roles require manual setup; a complete live agent workflow is not verified by the offline demo.
- GitHub posting is optional, requires external configuration and explicit approval, and is intended for the sandbox target.

