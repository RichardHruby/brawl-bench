#!/usr/bin/env bash
set -euo pipefail

# Conductor worktree setup script for brawl-bench
# Creates a fresh venv and copies secrets into the worktree.

python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt

cp "$CONDUCTOR_ROOT_PATH/.env" .env
