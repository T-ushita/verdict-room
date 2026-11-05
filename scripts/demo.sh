#!/usr/bin/env bash
# Offline demo.
set -euo pipefail
cd "$(dirname "$0")/../toolkit"
uv run verdict case 825 --offline
uv run verdict claims 825
