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

## Status
See `docs/BUILD_PLAN.md`. Anything mocked is listed under "Honest limitations" below.

## Honest limitations
- The UI is a local Docket backed by case/ledger JSON files, not a deployed service.
- Claim extraction is regex-based and heuristic.
- Check-run and PR-file fixtures may be missing; unavailable evidence is reported as `UNVERIFIED`.
- Switch room communication has not been verified by this CLI.
- GitHub live posting remains guarded and is not implemented yet.
