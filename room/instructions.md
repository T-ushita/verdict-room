# Room instructions: Verdict Room
Purpose: help a maintainer decide between competing PRs for one issue.
Case = one issue. Facts come from the `verdict` CLI, never from memory.

Switch setup:
- Add the Clerk, Examiner, Skeptic, and Registrar prompts as room roles.
- Invite a second agent/provider for the Skeptic when available.
- Share this file, docs/ARCHITECTURE.md, and the cases/<issue>/ files as room documents/references.
- Start work by addressing a role or agent explicitly, e.g. `@Clerk case 820`.

Flow: Clerk -> Examiner -> Skeptic -> (maintainer decision) -> Registrar.
Hard rules for everyone:
- Cite evidence links. A claim without evidence is UNVERIFIED.
- Do not call any GitHub write API. Only the Registrar may post, and only after `approval.json` exists.
- Say "I don't know" when evidence is missing. Do not guess.
- Keep room messages short. Put detail in `cases/<id>/` files.
- Status vocabulary: VERIFIED, UNVERIFIED, CONTRADICTED, NOT_CHECKABLE.
