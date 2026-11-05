# Registrar
Trigger: maintainer approves the ruling in the room.
Do: `verdict ruling <case> --draft` and show it. After the maintainer writes `approve <hash>`, run `verdict ruling <case> --post --live`.
Never post without `approval.json`. Default to dry-run. Target repo must equal VERDICT_REPO.
