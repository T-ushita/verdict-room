default:
    @just --list
setup:
    cd toolkit && uv sync
test:
    cd toolkit && uv run pytest -q
check:
    cd toolkit && uv run ruff check . && uv run ruff format --check .
case issue:
    cd toolkit && uv run verdict case {{issue}}
ui:
    cd toolkit && uv run verdict serve
demo:
    bash scripts/demo.sh
