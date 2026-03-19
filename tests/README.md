# Pytest suite

Unit and API tests that run **out of the box** with no real LLM, vault, or agent-config:

- **tenant_exists** is patched to `True` for API tests, so no Redis or AI Config is required.
- **run_survey_summary_crew** is patched in the `client` fixture to return mock data, so no real LLM is called.
- No server needs to be running; tests use FastAPI’s `TestClient`.

## Run all tests

From the project root:

```bash
make test
# or
uv run pytest tests/ -v
# or
.venv/bin/python -m pytest tests/ -v
```

- `make test-unit` – unit tests only
- `make test-api` – API route tests only

## Test layout

| Module | What it tests |
|--------|----------------|
| `test_api_routes.py` | Health, probes, POST /survey-summary, WebSocket /ws/survey-summary |
| `test_agent_service.py` | Config helpers, `build_survey_summary_inputs`, `generate_response` |
| `test_schemas.py` | Request/response models, `SurveyDataRequest` validators |
| `test_tenant.py` | `TenantConfigUnavailableError`, `_ai_config_base_url_or_none`, `tenant_exists` error path |
| `test_constants.py` | API constants and config paths |
| `test_kafka_pipeline.py` | `get_kafka_status`, `_kafka_bootstrap_servers`, `_parse_request_and_correlation_id` |
| `test_exceptions.py` | AppException hierarchy and handler registration |

## Markers

- `@pytest.mark.unit` – unit tests (no app)
- `@pytest.mark.api` – tests that hit the FastAPI app via `TestClient`

Run only unit tests: `pytest tests/ -v -m unit`
