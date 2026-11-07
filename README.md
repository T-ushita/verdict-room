# Verdict Room

A maintainer-side PR desk built on [Switch](https://docs.switchagents.ai/).
When several PRs target the same issue, a Switch room opens a **case**: agents
group the PRs, check each PR's claims against evidence (CI, diff, tests), argue
about the findings, and hand a short **ruling draft** to a human maintainer.
Nothing is posted to GitHub until the maintainer approves it in the room.

> Hackathon: Flip the Switch (Track 1, Best Business Workflow).
> Demo target: real duplicate PR clusters on `sandbox-quantum/switch`
> (e.g. issue #820 and #825 as of the Nov 4 2026 snapshot — re-verify live).

## The problem
Duplicate PRs for one issue are common. Maintainers re-read the same issue,
cross-check "tests passed" claims by hand, and decide who wins. A big test count
can hide that the feature does not work end to end.

## Workflow
1. Maintainer posts `case 820` in the room.
2. **Clerk** builds the case file: issue, acceptance criteria, all linked PRs.
3. **Examiner** extracts each PR's claims and checks them with the `verdict` toolkit.
4. **Skeptic** (a different agent/provider) tries to break the Examiner's findings.
5. **Maintainer** reads the claim ledger (UI or room), picks an outcome.
6. **Registrar** posts the approved comments. Default is dry-run.

## Where Switch is essential
- One room per case holds the case file, roles, and the full debate as shared context.
- Agents are separate named teammates (different runtimes) that can disagree in the open.
- The human approval gate lives in the room. No approval, no GitHub write.
- See `docs/ARCHITECTURE.md`.

## Quick start
Create a local `.env` file; add tokens only when needed. `.env` is ignored by Git.

```bash
just setup
just case 825               # live fetch, or add --offline where supported
cd toolkit && uv run pytest -q
cd toolkit && uv run verdict ledger 825 --offline
cd toolkit && uv run verdict serve
```
Open `http://127.0.0.1:8787`.

Offline demo: use `--offline` commands with `fixtures/`. Issue 825 is currently a
fixture-backed snapshot, not a claim that the recorded GitHub data is live.

For the sandbox live-post gate, use issue
[#1 in T-ushita/verdict-room-sandbox](https://github.com/T-ushita/verdict-room-sandbox/issues/1)
as `VERDICT_POST_ISSUE`. Keep `GITHUB_WRITE_TOKEN` out of room prompts and agent
sessions; enter it only in the trusted terminal session that invokes
`verdict ruling 825 --live`.

## Scheduled PR scanning

The repository includes `.github/workflows/verdict-scan.yml`. It scans hourly and
on manual dispatch, stores a fingerprint for every PR, and reports only new or
changed PRs.

The state file is `cases/pr-state.json`. A PR is rescored only when its head SHA,
updated time, open/closed/merged state, draft state, title, or body changes.
Unchanged, merged, and closed PRs are recorded without rerunning claim or evidence
checks. The workflow scan summary is written to the GitHub Actions run summary.

Switch room creation and agent notification are not automatic yet. The scheduled
job reports detected cases and changed PRs; a maintainer or future Switch
automation can address `@yellow-clerk case <issue>`.

## Status
See `docs/BUILD_PLAN.md`. Anything mocked is listed under "Honest limitations" below.

## Honest limitations
- The UI is a local Docket backed by case/ledger JSON files, not a deployed service.
- Claim extraction is regex-based and heuristic.
- Check-run and PR-file fixtures may be missing; unavailable evidence is reported as `UNVERIFIED`.
- Switch room communication has not been verified by this CLI.
- GitHub live posting is implemented but remains unverified against a sandbox verdict-log issue.
