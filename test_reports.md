# Test Report

| Field | Value |
|-------|-------|
| **Generated** | 2026-03-12 09:26:20 UTC |
| **Command** | `make check` (verbose) |
| **Status** | **PASSED** |

---

## Full output (verbose)

```
Resolved 212 packages in 4ms
Audited 209 packages in 44ms
Remove .mypy_cache.......................................................Passed
- hook id: remove-mypy-cache
- duration: 0.08s
pytest with coverage (fail under from pyproject).........................Passed
- hook id: pytest-coverage
- duration: 22.56s

============================= test session starts ==============================
platform darwin -- Python 3.12.12, pytest-9.0.2, pluggy-1.6.0 -- /Users/madhusudan.kumar/github_dir/ai-agent-boilerplate/.venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/madhusudan.kumar/github_dir/ai-agent-boilerplate
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.12.1, pytest_httpserver-1.1.5, asyncio-1.3.0, cov-7.0.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 126 items

tests/test_agent_service.py::test_build_survey_summary_inputs_dict_survey_data PASSED [  0%]
tests/test_agent_service.py::test_build_survey_summary_inputs_str_survey_data PASSED [  1%]
tests/test_agent_service.py::test_get_agent_runtime_config_has_endpoints PASSED [  2%]
tests/test_agent_service.py::test_is_rest_api_enabled_is_bool PASSED     [  3%]
tests/test_agent_service.py::test_is_websocket_enabled_is_bool PASSED    [  3%]
tests/test_agent_service.py::test_is_kafka_enabled_is_bool PASSED        [  4%]
tests/test_agent_service.py::test_run_survey_summary_crew_returns_mock_when_patched PASSED [  5%]
tests/test_agent_service.py::test_generate_survey_summary_response_success_when_crew_mocked PASSED [  6%]
tests/test_agent_service.py::test_generate_survey_summary_response_failure_when_crew_raises PASSED [  7%]
tests/test_api_routes.py::test_root_and_health PASSED                    [  7%]
tests/test_api_routes.py::test_startup_live_ready_probes PASSED          [  8%]
tests/test_api_routes.py::test_survey_summary_rest PASSED                [  9%]
tests/test_api_routes.py::test_survey_summary_validation_error PASSED    [ 10%]
tests/test_api_routes.py::test_survey_summary_rest_strips_whitespace PASSED [ 11%]
tests/test_api_routes.py::test_survey_summary_rest_with_reasoning_effort[None] PASSED [ 11%]
tests/test_api_routes.py::test_survey_summary_rest_with_reasoning_effort[low] PASSED [ 12%]
tests/test_api_routes.py::test_survey_summary_rest_with_reasoning_effort[high] PASSED [ 13%]
tests/test_api_routes.py::test_survey_summary_rest_500_when_agent_returns_failure PASSED [ 14%]
tests/test_api_routes.py::test_websocket_survey_summary PASSED           [ 15%]
tests/test_api_routes.py::test_survey_summary_rest_404_when_rest_disabled PASSED [ 15%]
tests/test_api_routes.py::test_websocket_invalid_json_returns_error PASSED [ 16%]
tests/test_api_routes.py::test_websocket_validation_error_invalid_body PASSED [ 17%]
tests/test_api_routes.py::test_websocket_tenant_not_registered PASSED    [ 18%]
tests/test_api_routes.py::test_websocket_tenant_config_unavailable PASSED [ 19%]
tests/test_api_routes.py::test_websocket_crew_raises_returns_error PASSED [ 19%]
tests/test_api_routes.py::test_websocket_404_when_disabled PASSED        [ 20%]
tests/test_constants.py::test_router_prefix PASSED                       [ 21%]
tests/test_constants.py::test_default_model PASSED                       [ 22%]
tests/test_constants.py::test_master_config_path_exists PASSED           [ 23%]
tests/test_constants.py::test_agents_and_tasks_config_paths PASSED       [ 23%]
tests/test_constants.py::test_kafka_defaults PASSED                      [ 24%]
tests/test_constants.py::test_use_crewai_external_memory_is_bool PASSED  [ 25%]
tests/test_crew.py::test_insight_valid PASSED                            [ 26%]
tests/test_crew.py::test_insight_requires_at_least_one_comment_id PASSED [ 26%]
tests/test_crew.py::test_insight_max_five_comment_ids PASSED             [ 27%]
tests/test_crew.py::test_survey_summary_with_comments_valid PASSED       [ 28%]
tests/test_crew.py::test_survey_summary_with_comments_minimal PASSED     [ 29%]
tests/test_crew.py::test_survey_summary_with_comments_missing_required_raises PASSED [ 30%]
tests/test_db_connections.py::test_redis_load_master_config_default_path PASSED [ 30%]
tests/test_db_connections.py::test_redis_load_master_config_custom_path PASSED [ 31%]
tests/test_db_connections.py::test_is_redis_enabled_reads_config PASSED  [ 32%]
tests/test_db_connections.py::test_is_redis_enabled_true_when_set PASSED [ 33%]
tests/test_db_connections.py::test_redis_not_enabled_error PASSED        [ 34%]
tests/test_db_connections.py::test_redis_vault_unavailable_error_message PASSED [ 34%]
tests/test_db_connections.py::test_is_mongo_enabled_reads_config PASSED  [ 35%]
tests/test_db_connections.py::test_is_mongo_enabled_true_when_set PASSED [ 36%]
tests/test_db_connections.py::test_mongo_not_enabled_error PASSED        [ 37%]
tests/test_db_connections.py::test_mongo_vault_unavailable_error_message PASSED [ 38%]
tests/test_db_connections.py::test_is_sql_enabled_reads_config PASSED    [ 38%]
tests/test_db_connections.py::test_is_sql_enabled_true_when_set PASSED   [ 39%]
tests/test_db_connections.py::test_build_pg_uri_from_secret_host_only PASSED [ 40%]
tests/test_db_connections.py::test_build_pg_uri_from_secret_postgres_keys PASSED [ 41%]
tests/test_db_connections.py::test_build_pg_uri_from_secret_no_host_returns_none PASSED [ 42%]
tests/test_db_connections.py::test_sql_not_enabled_error PASSED          [ 42%]
tests/test_db_connections.py::test_sql_vault_unavailable_error_message PASSED [ 43%]
tests/test_exceptions.py::test_app_exception_defaults PASSED             [ 44%]
tests/test_exceptions.py::test_bad_request_error PASSED                  [ 45%]
tests/test_exceptions.py::test_forbidden_error PASSED                    [ 46%]
tests/test_exceptions.py::test_not_found_error PASSED                    [ 46%]
tests/test_exceptions.py::test_service_unavailable_error PASSED          [ 47%]
tests/test_exceptions.py::test_unprocessable_entity_error PASSED         [ 48%]
tests/test_exceptions.py::test_register_exception_handlers_does_not_raise PASSED [ 49%]
tests/test_exceptions.py::test_app_exception_returns_correct_status PASSED [ 50%]
tests/test_kafka_pipeline.py::test_kafka_bootstrap_servers_from_env PASSED [ 50%]
tests/test_kafka_pipeline.py::test_kafka_bootstrap_servers_default PASSED [ 51%]
tests/test_kafka_pipeline.py::test_is_kafka_enabled_reads_config PASSED  [ 52%]
tests/test_kafka_pipeline.py::test_parse_envelope PASSED                 [ 53%]
tests/test_kafka_pipeline.py::test_parse_envelope_missing_agent_id_raises PASSED [ 53%]
tests/test_kafka_pipeline.py::test_build_envelope PASSED                 [ 54%]
tests/test_kafka_pipeline.py::test_normalized_env_suffix PASSED          [ 55%]
tests/test_kafka_pipeline.py::test_make_ssl_context_no_verify PASSED     [ 56%]
tests/test_kafka_pipeline.py::test_process_one_message_async_returns_success_when_crew_mocked PASSED [ 57%]
tests/test_kafka_pipeline.py::test_load_master_config PASSED             [ 57%]
tests/test_kafka_pipeline.py::test_get_consumer_agent_id_from_env PASSED [ 58%]
tests/test_kafka_pipeline.py::test_get_consumer_agent_id_from_master_config PASSED [ 59%]
tests/test_kafka_pipeline.py::test_get_consumer_group_id_default PASSED  [ 60%]
tests/test_kafka_pipeline.py::test_get_consumer_group_id_from_env PASSED [ 61%]
tests/test_kafka_pipeline.py::test_get_max_poll_interval_ms_default PASSED [ 61%]
tests/test_kafka_pipeline.py::test_get_max_poll_interval_ms_from_env PASSED [ 62%]
tests/test_kafka_pipeline.py::test_get_processing_timeout_seconds PASSED [ 63%]
tests/test_kafka_pipeline.py::test_start_kafka_pipeline_thread_returns_none_when_disabled PASSED [ 64%]
tests/test_kafka_pipeline.py::test_start_kafka_pipeline_thread_returns_thread_when_enabled PASSED [ 65%]
tests/test_logging_config.py::test_resolve_log_level_explicit PASSED     [ 65%]
tests/test_logging_config.py::test_resolve_log_level_strips_whitespace PASSED [ 66%]
tests/test_logging_config.py::test_resolve_log_level_invalid_falls_back_to_env_or_default PASSED [ 67%]
tests/test_logging_config.py::test_resolve_log_level_env_ai_infra_takes_precedence PASSED [ 68%]
tests/test_logging_config.py::test_configure_logging_does_not_raise PASSED [ 69%]
tests/test_logging_config.py::test_get_logger_without_crew_context_returns_logger PASSED [ 69%]
tests/test_logging_config.py::test_get_logger_returns_logger PASSED      [ 70%]
tests/test_logging_config.py::test_event_span_success PASSED             [ 71%]
tests/test_logging_config.py::test_event_span_raises_and_logs PASSED     [ 72%]
tests/test_logging_config.py::test_mandatory_from_start PASSED           [ 73%]
tests/test_logging_config.py::test_make_end_payload_crew_run PASSED      [ 73%]
tests/test_logging_config.py::test_make_end_payload_database PASSED      [ 74%]
tests/test_logging_config.py::test_make_end_payload_memory_load PASSED   [ 75%]
tests/test_logging_config.py::test_make_end_payload_memory_save PASSED   [ 76%]
tests/test_logging_config.py::test_make_end_payload_memory_search PASSED [ 76%]
tests/test_logging_config.py::test_make_end_payload_unknown_type_raises PASSED [ 77%]
tests/test_main.py::test_run_hooks_exits_zero_when_precommit_succeeds PASSED [ 78%]
tests/test_main.py::test_run_hooks_exits_nonzero_when_precommit_fails PASSED [ 79%]
tests/test_main.py::test_run_hooks_exits_one_when_precommit_not_found PASSED [ 80%]
tests/test_schemas.py::test_health_response PASSED                       [ 80%]
tests/test_schemas.py::test_probe_response PASSED                        [ 81%]
tests/test_schemas.py::test_survey_data_request_strip_tenant_fields PASSED [ 82%]
tests/test_schemas.py::test_survey_data_request_minimal PASSED           [ 83%]
tests/test_schemas.py::test_survey_data_request_missing_required_raises PASSED [ 84%]
tests/test_schemas.py::test_survey_summary_response_success PASSED       [ 84%]
tests/test_schemas.py::test_survey_summary_response_failure PASSED       [ 85%]
tests/test_schemas.py::test_survey_data_request_reasoning_effort_valid[None-None] PASSED [ 86%]
tests/test_schemas.py::test_survey_data_request_reasoning_effort_valid[low-low] PASSED [ 87%]
tests/test_schemas.py::test_survey_data_request_reasoning_effort_valid[  LOW  -low] PASSED [ 88%]
tests/test_schemas.py::test_survey_data_request_reasoning_effort_valid[Medium-medium] PASSED [ 88%]
tests/test_schemas.py::test_survey_data_request_reasoning_effort_valid[HIGH-high] PASSED [ 89%]
tests/test_schemas.py::test_survey_data_request_reasoning_effort_invalid[invalid] PASSED [ 90%]
tests/test_schemas.py::test_survey_data_request_reasoning_effort_invalid[super] PASSED [ 91%]
tests/test_schemas.py::test_survey_data_request_reasoning_effort_invalid[] PASSED [ 92%]
tests/test_schemas.py::test_error_detail PASSED                          [ 92%]
tests/test_tenant.py::test_tenant_config_unavailable_error PASSED        [ 93%]
tests/test_tenant.py::test_ai_config_base_url_from_env PASSED            [ 94%]
tests/test_tenant.py::test_ai_config_base_url_fallback_keys PASSED       [ 95%]
tests/test_tenant.py::test_tenant_exists_raises_when_sdk_missing PASSED  [ 96%]
tests/test_tenant.py::test_tenant_exists_true_when_connection_mocked PASSED [ 96%]
tests/test_tenant.py::test_tenant_exists_false_when_connection_mocked PASSED [ 97%]
tests/test_tools.py::test_my_custom_tool_input_valid PASSED              [ 98%]
tests/test_tools.py::test_my_custom_tool_input_missing_raises PASSED     [ 99%]
tests/test_tools.py::test_my_custom_tool_has_schema_and_run PASSED       [100%]

================================ tests coverage ================================
______________ coverage: platform darwin, python 3.12.12-final-0 _______________

Name                                          Stmts   Miss Branch BrPart  Cover   Missing
-----------------------------------------------------------------------------------------
src/agent/api/agent_service.py                   65      1      8      2    96%   45->47, 216
src/agent/api/constants.py                       51      2      0      0    96%   92-93
src/agent/api/exceptions.py                      55      4      0      0    93%   179-180, 192-193
src/agent/api/routes.py                         117     13     14      1    86%   98-109, 217-219, 294-295, 330-331
src/agent/api/schemas.py                         49      1      4      1    96%   71
src/agent/api/tenant.py                          36     19      4      1    45%   25, 39-48, 53-76
src/agent/crew.py                                35      6      2      0    78%   77, 118, 129, 151-153
src/agent/main.py                                34      7      0      0    79%   37-141
src/agent/tools/custom_tool.py                   11      0      0      0   100%
src/agent/utils/logging_config/base.py            8      0      0      0   100%
src/agent/utils/logging_config/config.py         25      0      0      0   100%
src/agent/utils/logging_config/constants.py       8      0      0      0   100%
src/agent/utils/logging_config/context.py        11      0      0      0   100%
src/agent/utils/logging_config/crew_run.py       26      0      0      0   100%
src/agent/utils/logging_config/database.py       27      0      0      0   100%
src/agent/utils/logging_config/events.py         30      0     10      0   100%
src/agent/utils/logging_config/memory.py         67      0      0      0   100%
src/agent/utils/paths.py                          2      0      0      0   100%
-----------------------------------------------------------------------------------------
TOTAL                                           657     53     42      5    91%
Required test coverage of 90.0% reached. Total coverage: 90.56%
============================= 126 passed in 16.18s =============================

trim trailing whitespace.................................................Passed
- hook id: trailing-whitespace
- duration: 0.09s
fix end of files.........................................................Passed
- hook id: end-of-file-fixer
- duration: 0.1s
check yaml...............................................................Passed
- hook id: check-yaml
- duration: 0.08s
check for added large files..............................................Passed
- hook id: check-added-large-files
- duration: 0.23s
check for merge conflicts................................................Passed
- hook id: check-merge-conflict
- duration: 0.16s
debug statements (python)................................................Passed
- hook id: debug-statements
- duration: 0.11s
isort....................................................................Passed
- hook id: isort
- duration: 0.18s
black....................................................................Passed
- hook id: black
- duration: 0.19s

All done! ✨ 🍰 ✨
56 files left unchanged.

flake8...................................................................Passed
- hook id: flake8
- duration: 0.53s
mypy.....................................................................Passed
- hook id: mypy
- duration: 2.36s

setup_agent.py:90: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
setup_agent.py:928: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
setup_agent.py:977: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
setup_agent.py:1055: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
Success: no issues found in 56 source files

```
