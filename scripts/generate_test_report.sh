#!/usr/bin/env bash
# Generate test_reports.md by running check with verbose output from all tools.
# Run from repo root: make test-report (or ./scripts/generate_test_report.sh)
# make test-report ensures setup-hooks runs first.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

REPORT_FILE="${REPO_ROOT}/test_reports.md"
TMP_OUTPUT=$(mktemp)
trap 'rm -f "$TMP_OUTPUT"' EXIT

# Same steps as make check, but with verbose pre-commit and no color (clean report)
export PRE_COMMIT_COLOR=never
export NO_COLOR=1
export PYTEST_ADDOPTS="-v --tb=long -ra"

echo "Running sync and pre-commit (verbose)..."
(
    uv sync --extra dev
    uv run pre-commit run --all-files -v
) > "$TMP_OUTPUT" 2>&1

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    STATUS="PASSED"
else
    STATUS="FAILED"
fi

TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M:%S UTC')

{
    echo "# Test Report"
    echo ""
    echo "| Field | Value |"
    echo "|-------|-------|"
    echo "| **Generated** | $TIMESTAMP |"
    echo "| **Command** | \`make check\` (verbose) |"
    echo "| **Status** | **$STATUS** |"
    echo ""
    echo "---"
    echo ""
    echo "## Full output (verbose)"
    echo ""
    echo '```'
    cat "$TMP_OUTPUT"
    echo '```'
} > "$REPORT_FILE"

echo "Report written to $REPORT_FILE (Status: $STATUS)"

exit $EXIT_CODE
