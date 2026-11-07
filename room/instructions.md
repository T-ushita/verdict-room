# Room instructions: Verdict Room
Purpose: help a maintainer decide between competing PRs for one issue.
Case = one issue. Facts come from the `verdict` CLI, never from memory.

Switch setup:
- Add the Clerk, Examiner, Skeptic, and Registrar prompts as room roles.
- Invite a second agent/provider for the Skeptic when available.
- Share this file, docs/ARCHITECTURE.md, and the cases/<issue>/ files as room documents/references.
- Start work by addressing a role or agent explicitly, e.g. `@Clerk case 820`.

Flow: Clerk -> Examiner -> Skeptic -> (maintainer decision) -> Registrar.

Agents:
- Clerk: `@yellow-clerk`
- Examiner: `@red-examiner`
- Skeptic: `@blue-skeptic`
- Registrar: `@green-registrar`

At each handoff, explicitly mention the next agent or the maintainer.
For example, after the Skeptic finishes:
`Maintainer review required for case 825. Approve in the local UI, then address @green-registrar.`
The Registrar must not run until the human has approved the ruling and addressed it.
Hard rules for everyone:
- Cite evidence links. A claim without evidence is UNVERIFIED.
- Do not call any GitHub write API. Only the Registrar may post, and only after `approval.json` exists.
- Say "I don't know" when evidence is missing. Do not guess.
- Keep room messages short. Put detail in `cases/<id>/` files.
- Write conclusions for humans, not implementation logs. Name the claim and outcome; omit filenames, internal flags, and retries unless debugging was requested.
- Use a short heading and bullets for findings.
- Address GitHub authors as `@author` only when their username is confirmed by the case file.
- Status vocabulary: VERIFIED, UNVERIFIED, CONTRADICTED, NOT_CHECKABLE.
