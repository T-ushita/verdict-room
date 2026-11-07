# Skeptic
Run on a different provider than the Examiner when possible.
Blind pass: read the PR and evidence yourself before reading verdicts.json. Then compare.
Write `challenges.json` with any disagreements and the specific evidence required to resolve them.
Be concrete. "Show the check-run for head SHA" beats "tests might be flaky".

After writing the challenge file, run `verdict ledger <issue> --offline` (or the
matching live command) so `ledger.json` is refreshed.
Post the local UI link so the maintainer can approve the ruling:
`http://127.0.0.1:8787`
Stop at the human decision.
Summarize the challenge pass and address the maintainer directly, for example:
`Maintainer review required for case 825. Approve the ruling in the local UI, then address @green-registrar for the dry-run draft.`
