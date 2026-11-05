# Registrar
Trigger: maintainer approves the ruling in the UI.
Do: `verdict ruling <issue> --draft` and show it. The local UI writes approval.json after human approval.
Never write approval.json and never post without it. Default to dry-run. Target repo must equal VERDICT_POST_REPO.
