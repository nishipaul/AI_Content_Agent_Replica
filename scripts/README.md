# Endpoint test scripts

Scripts to test API endpoints (excluding health and probe APIs).

## Endpoints tested

| Script | Method | Endpoint | Description |
|--------|--------|----------|-------------|
| `test_survey_summary_rest.py` | POST | `/v1/ai-content-agent/survey-summary` | Survey summary (REST) |
| `test_survey_summary_ws.py` | WebSocket | `/v1/ai-content-agent/ws/survey-summary` | Survey summary (WebSocket) |

## Prerequisites

- Server running: `make run` (or `uv run uvicorn agent.api:app --reload --host 0.0.0.0 --port 8000`)
- `requests` (for REST tests); `websockets` (for WS test). Install with: `uv add requests websockets` or `pip install requests websockets`

## Test matrix

Each script runs **4 test cases** covering all combinations of:

| API mode | reasoning_effort |
|----------|-----------------|
| `completions` | `None` (omitted) |
| `completions` | `low` |
| `responses` | `None` (omitted) |
| `responses` | `low` |

## Configuration (`.env`)

All scripts automatically load the repo's `.env` file (via `python-dotenv`) for
tenant ID, service name, and other shared values. The following variables are
read from `.env` (or can be overridden via the shell environment):

- **SMTIP_TID** – Tenant ID (**required**, set in `.env`)
- **SMTIP_FEATURE** – Feature / service name (**required**, set in `.env`)
- **AGENT_NAME** – Agent / service name (default: `survey-summary`)
- **BASE_URL** – Base URL (default: `http://0.0.0.0:8000`)
- **LLM_COMPLETIONS_MODEL** – Model for completions API tests (default: `auto-route`)
- **LLM_RESPONSES_MODEL** – Model for responses API tests (default: same as `LLM_COMPLETIONS_MODEL`)
- **SKIP_DISABLED_ENDPOINTS** – Set to `1` to skip tests for disabled endpoints (e.g. WebSocket returns 404). When unset, all tests are run and must pass (for local runs).

> **Note:** `sample_curl.sh` also sources `.env` for `SMTIP_TID`, `SMTIP_FEATURE`, and `BASE_URL`.

## Run a single test

```bash
# From project root (with server running in another terminal: make run)
uv run python scripts/test_survey_summary_rest.py
uv run python scripts/test_survey_summary_ws.py
```

## Run all tests

```bash
make scripts-test
# or
uv run python scripts/run_all_tests.py
```

When running locally, **all endpoint tests are run** and the suite fails if any endpoint is unavailable (e.g. WebSocket disabled). Enable `websocket_enabled` in `master_config.yaml` under `agent_runtime_config.endpoints` so the WebSocket test passes.

To skip tests for disabled endpoints (e.g. in CI where WebSocket may be off):

```bash
SKIP_DISABLED_ENDPOINTS=1 uv run python scripts/run_all_tests.py
```

Exit code 0 if all pass (or skipped), 1 if any fail.
