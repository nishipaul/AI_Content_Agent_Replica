# AI Agent Boilerplate – Makefile
# Run tests, API server, pre-commit checks, and common dev tasks.
# Usage: make [target]; override PORT=8000 HOST=0.0.0.0 as needed.

.PHONY: help test test-unit test-api test-cov run run-api scripts-test install hooks
.PHONY: sync check setup-hooks setup-merge-driver test-report push clean

# Defaults (override: make run PORT=5000)
PORT ?= 8000
HOST ?= 0.0.0.0

help:
	@echo "AI Agent Boilerplate – targets:"
	@echo "  make sync          – install dependencies (including dev)"
	@echo "  make test          – run pytest (unit + API, no LLM/vault)"
	@echo "  make test-unit     – run unit tests only"
	@echo "  make test-api      – run API route tests only"
	@echo "  make test-cov      – run tests with coverage"
	@echo "  make test-report   – run check (verbose) and write test_reports.md"
	@echo "  make run           – start API server (uvicorn, reload)"
	@echo "  make run-api       – same as run (alias)"
	@echo "  make scripts-test  – run endpoint scripts (server must be running)"
	@echo "  make install       – install deps (uv sync)"
	@echo "  make hooks        – run pre-commit on all files"
	@echo "  make setup-hooks   – install pre-commit and pre-push hooks (run once after clone)"
	@echo "  make check         – sync + run pre-commit on all files"
	@echo "  make push         – run check, then git push (use for all pushes)"
	@echo "  make clean        – remove dist/, .mypy_cache, __pycache__, .pytest_cache"
	@echo ""
	@echo "Overrides: PORT=8000 HOST=0.0.0.0 (e.g. make run PORT=5000)"

sync:
	uv sync --extra dev

# Pytest: all tests (mocked crew/tenant, no real LLM/vault)
test:
	uv run pytest tests/ -v --tb=short

test-unit:
	uv run pytest tests/ -v -m unit --tb=short

test-api:
	uv run pytest tests/ -v -m api --tb=short

test-cov: sync
	PYTHONPATH=src uv run pytest --cov=agent --cov-report=term-missing --cov-fail-under=80

test-report: setup-hooks
	./scripts/generate_test_report.sh

setup-hooks: sync setup-merge-driver
	uv run pre-commit install
	uv run pre-commit install --hook-type pre-push
	@echo "Pre-commit and pre-push hooks installed."

setup-merge-driver:
	@chmod +x scripts/merge_driver_test_report.sh
	@git config merge.regenerate-test-report.name "Regenerate test_reports.md"
	@git config merge.regenerate-test-report.driver "scripts/merge_driver_test_report.sh %%O %%A %%B %%P"
	@echo "Merge driver for test_reports.md installed. On merge, the file will be regenerated."

check: sync
	uv run pre-commit run --all-files

push: check setup-hooks
	@if [ -n "$$(git status --short)" ]; then \
		echo "You have uncommitted changes."; \
		echo "Commit all and push? [y/N] (N = abort push, leave changes uncommitted)"; \
		read resp; \
		case "$$resp" in y|Y) \
			git add -A && git commit -m "chore: commit before push"; \
			;; \
		*) \
			echo "Push aborted. Commit or stash your changes, then run make push again."; \
			exit 1; \
			;; \
		esac; \
	fi
	@echo "Pushing..."
	git push --no-verify $(PUSH_ARGS)

clean:
	rm -rf dist/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache/
	@echo "Cleaned dist, .mypy_cache, __pycache__, .pytest_cache"

# Start API server (as in README / scripts)
run run-api:
	uv run uvicorn agent.api:app --reload --host $(HOST) --port $(PORT)

# Endpoint scripts (require server: make run in another terminal)
scripts-test:
	uv run python scripts/run_all_tests.py

install:
	uv sync

# Pre-commit: lint, format, type-check
hooks:
	uv run pre-commit run --all-files
