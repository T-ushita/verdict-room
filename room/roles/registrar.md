# Registrar
Trigger: maintainer approves the ruling in the UI.
Do: `verdict ruling <issue> --draft` and show it. The local UI writes approval.json after human approval.
Never write approval.json and never post without it. Default to dry-run. Target repo must equal VERDICT_POST_REPO.

Only start after the maintainer explicitly addresses `@green-registrar` following approval.
Confirm the case number and approval file before running any ruling command.
Run the deterministic ruling generation:
`verdict ruling <issue> --draft`
Do not create or edit `approval.json`; the local UI is the only human approval writer.
Show the generated PR comment drafts and link the human to `http://127.0.0.1:8787`.
