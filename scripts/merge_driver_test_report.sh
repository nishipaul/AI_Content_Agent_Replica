#!/usr/bin/env bash
# Merge driver for test_reports.md: on conflict, replace with a freshly generated report.
# Git calls this with: %O %A %B %P (ancestor, ours, theirs, path). We overwrite %A with new content.
set -e
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
# Regenerate report (skip auto-commit during merge). Writes to test_reports.md (= %A when run from repo root).
SKIP_AUTO_COMMIT_TEST_REPORT=1 "$REPO_ROOT/scripts/generate_test_report.sh" || true
exit 0
