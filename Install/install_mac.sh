#!/usr/bin/env bash
# Install script for macOS – ensures Python 3.12+, uv, and project .venv are ready.
# Run from anywhere; repo root is inferred from this script’s location.

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=12

echo "==> Repo root: $REPO_ROOT"
cd "$REPO_ROOT"

# --- Check Python 3.12+ ---
check_python() {
  for cmd in python3.12 python3 python; do
    if command -v "$cmd" &>/dev/null; then
      ver="$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)" || continue
      major="${ver%%.*}"
      minor="${ver#*.}"
      minor="${minor%%.*}"
      if [[ "$major" -ge "$MIN_PYTHON_MAJOR" ]] && [[ "$minor" -ge "$MIN_PYTHON_MINOR" ]]; then
        echo "$cmd"
        return
      fi
    fi
  done
  return 1
}

PYTHON="$(check_python)" || true
if [[ -z "$PYTHON" ]]; then
  echo "ERROR: Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR} or higher is required."
  echo "Install it with: brew install python@3.12"
  exit 1
fi

echo "==> Using Python: $("$PYTHON" --version)"

# --- Install uv if missing ---
if ! command -v uv &>/dev/null; then
  echo "==> Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${PATH}"
  if ! command -v uv &>/dev/null; then
    echo "ERROR: uv was installed but not found in PATH. Add ~/.local/bin to PATH and re-run."
    exit 1
  fi
else
  echo "==> uv already installed: $(uv --version)"
fi

# --- Create .venv and install dependencies ---
echo "==> Creating .venv and syncing dependencies with uv..."
uv sync --frozen

echo ""
echo "==> Install complete."
echo "    Activate the environment:  source .venv/bin/activate"
echo "    Run the API server:        uv run uvicorn agent.api:app --host 0.0.0.0 --port 5000"
echo "    Or from repo root:        uv run run_api"
