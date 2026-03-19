#!/usr/bin/env bash
#
# Mandatory: install pre-commit and pre-push hooks so no code can be committed
# or pushed without passing checks. Run once after clone (from repo root).
#
#   ./scripts/setup_hooks.sh
#
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "Installing dev dependencies..."
uv sync --extra dev --quiet

echo "Installing pre-commit hook (runs before 'git commit')..."
uv run pre-commit install

echo "Installing pre-push hook (runs before 'git push')..."
uv run pre-commit install --hook-type pre-push

# Verify hooks are in place
GIT_DIR="${GIT_DIR:-$REPO_ROOT/.git}"
if [ -f "$GIT_DIR/hooks/pre-commit" ] && [ -f "$GIT_DIR/hooks/pre-push" ]; then
  echo "Done. Verified: pre-commit and pre-push hooks are installed."
  echo "  pre-commit: $GIT_DIR/hooks/pre-commit"
  echo "  pre-push:   $GIT_DIR/hooks/pre-push"
else
  echo "WARNING: Hook files not found. Ensure you run this from the repo root and .git exists."
  exit 1
fi
