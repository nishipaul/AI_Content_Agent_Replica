#!/usr/bin/env python
"""
Integration test: structured logging at all log levels (DEBUG, INFO, WARNING, ERROR).

Exercises agent.utils.logging_config: configure_logging, get_logger (with/without context),
event_span with CrewRunStartEvent, log_error. Verifies level-based behavior:
- DEBUG: crew_run start/end + error with traceback
- INFO: crew_run start/end + error without traceback
- WARNING/ERROR: only error events logged

Evaluation – what is tested per level:

  Component        | Events under test (DEBUG/INFO)     | Asserted
  -----------------|-----------------------------------|---------------------------
  agent_service    | crew_run (start/end)              | component, event names
  api              | free-form event (e.g. health)      | component
  kafka_pipeline   | free-form event                   | component (when run)
  error            | error (message, error_type)        | traceback at DEBUG only

  Levels:
  - DEBUG: start/end + error with traceback; assert "traceback" / DEBUG_ONLY_TRACEBACK_SENTINEL.
  - INFO: start/end + error without traceback; assert DEBUG_ONLY_TRACEBACK_SENTINEL not present.
  - WARNING/ERROR: only error; assert "error" in output.

Run from project root:

  uv run python scripts/test_logging_all_packages.py
  uv run python scripts/test_logging_all_packages.py --level DEBUG

Exit code 0 = all checks passed, 1 = failure.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
from contextlib import redirect_stderr

# When invoked with --level <LEVEL>, set env before any logging imports
if "--level" in sys.argv:
    try:
        i = sys.argv.index("--level")
        _level = sys.argv[i + 1] if i + 1 < len(sys.argv) else "INFO"
        if _level.upper() in ("DEBUG", "INFO", "WARNING", "ERROR"):
            os.environ["AI_INFRA_LOG_LEVEL"] = _level.upper()
    except (IndexError, ValueError):
        pass

# Project root and .env (script lives in scripts/)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.abspath(os.path.join(_script_dir, os.pardir))
_env_file = os.path.join(_repo_root, ".env")
if os.path.isfile(_env_file):
    try:
        from dotenv import load_dotenv

        load_dotenv(_env_file)
    except ImportError:
        pass

# Paths for imports (agent lives under src/)
_src = os.path.join(_repo_root, "src")
if _src not in sys.path:
    sys.path.insert(0, _src)


LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")
DEBUG_ONLY_TRACEBACK_SENTINEL = "DEBUG_ONLY_TRACEBACK_SENTINEL"


def _run_core_logging(log_level: str) -> None:
    """Agent logging: crew_run (event_span), get_logger with/without context, log_error."""
    from agent.utils.logging_config import (
        CrewRunStartEvent,
        configure_logging,
        event_span,
        get_logger,
        get_logger_without_crew_context,
        log_error,
    )

    configure_logging(level=log_level or os.environ.get("AI_INFRA_LOG_LEVEL") or "INFO")
    # Request-scoped logger (agent_service style)
    log = get_logger(
        "agent_service",
        tenant_id="test-tenant",
        service_name="test-service",
        agent_id="test-agent",
        session_id="test-session",
        component="agent_service",
    )
    start_payload = CrewRunStartEvent(
        tenant_id="test-tenant",
        service_name="test-service",
        agent_id="test-agent",
        session_id="test-session",
        operation="survey_summary",
        stream=False,
    )
    with event_span(log, start_payload, input_data={"locale": "en-US"}):
        pass
    # Logger without crew context (api / kafka_pipeline style)
    api_log = get_logger_without_crew_context("api")
    api_log.info("health_check_requested")
    kafka_log = get_logger_without_crew_context("kafka_pipeline")
    kafka_log.info("kafka_pipeline_test_event", message="test")
    # Error with traceback sentinel: DEBUG includes it, INFO does not
    log_error(
        log,
        "Test error message",
        error_type="ValueError",
        traceback_str=f"{DEBUG_ONLY_TRACEBACK_SENTINEL}\n  File test_logging",
    )


def _only_errors_level(level: str) -> bool:
    return level.upper() in ("WARNING", "ERROR")


def _run_all_logging_at_level(level: str) -> tuple[str, Exception | None]:
    """Run all logging at level; capture stderr. Returns (combined_output, import_error)."""
    combined = io.StringIO()
    import_error: Exception | None = None
    with redirect_stderr(combined):
        try:
            from agent.utils import logging_config  # noqa: F401
        except ImportError as e:
            import_error = e
        if import_error is None:
            _run_core_logging(level)
    return combined.getvalue(), import_error


ALL_EVENT_NAMES = (
    "crew_run",
    "health_check_requested",
    "kafka_pipeline_test_event",
    "error",
)
ALL_COMPONENTS = (
    "agent_service",
    "api",
    "kafka_pipeline",
)


def _compute_log_stats(combined: str) -> tuple[int, dict[str, int], dict[str, int]]:
    """Returns (total_lines, event_counts, component_counts)."""
    lines = [ln.strip() for ln in combined.splitlines() if ln.strip()]
    json_like = [
        ln
        for ln in lines
        if '"event"' in ln or '"timestamp"' in ln or "event_phase" in ln
    ]
    total = len(json_like)
    event_counts: dict[str, int] = {e: 0 for e in ALL_EVENT_NAMES}
    component_counts: dict[str, int] = {c: 0 for c in ALL_COMPONENTS}
    for ln in json_like:
        for e in ALL_EVENT_NAMES:
            if e in ln:
                event_counts[e] += 1
                break
        for c in ALL_COMPONENTS:
            if c in ln:
                component_counts[c] += 1
                break
    return total, event_counts, component_counts


def _print_logging_summary(level: str, combined: str) -> None:
    """Print summary of what logging was detected at this level."""
    only_errors = _only_errors_level(level)
    print(f"\n--- Logging summary [{level}] ---")
    if only_errors:
        has_error = "error" in combined
        print("  (WARNING/ERROR: only error events logged)")
        print(f"  error event: {'✓' if has_error else '✗'}")
        total, event_counts, _ = _compute_log_stats(combined)
        print("  --- Stats ---")
        print(f"  Total log lines: {total}")
        if event_counts.get("error", 0) > 0:
            print(f"  Event counts: error={event_counts['error']}")
        print()
        return
    for comp in ALL_COMPONENTS:
        comp_ok = comp in combined
        print(f"  {comp}: component={'✓' if comp_ok else '-'}")
    print(f"  crew_run: {'✓' if 'crew_run' in combined else '-'}")
    print(f"  error: {'✓' if 'error' in combined else '-'}")
    if level == "DEBUG":
        print(f"  traceback in error: {'✓' if 'traceback' in combined else '-'}")
    elif level == "INFO":
        print(
            f"  traceback omitted (INFO): {'✓' if DEBUG_ONLY_TRACEBACK_SENTINEL not in combined else '✗'}"
        )
    total, event_counts, component_counts = _compute_log_stats(combined)
    print("  --- Stats ---")
    print(f"  Total log lines: {total}")
    events_with_count = [
        (e, event_counts[e]) for e in ALL_EVENT_NAMES if event_counts[e] > 0
    ]
    if events_with_count:
        print(
            f"  Event counts: {', '.join(f'{e}={n}' for e, n in sorted(events_with_count, key=lambda x: -x[1]))}"
        )
    comps_with_count = [
        (c, component_counts[c]) for c in ALL_COMPONENTS if component_counts[c] > 0
    ]
    if comps_with_count:
        print(
            f"  Component counts: {', '.join(f'{c}={n}' for c, n in sorted(comps_with_count, key=lambda x: -x[1]))}"
        )
    print()


def _run_single_level(level: str) -> int:
    failures: list[str] = []
    only_errors = _only_errors_level(level)
    combined, import_error = _run_all_logging_at_level(level)
    if import_error is not None:
        print(
            "FAIL: Could not import agent.utils.logging_config. "
            "Run from project root: uv run python scripts/test_logging_all_packages.py"
        )
        print("Error:", import_error)
        return 1

    _print_logging_summary(level, combined)

    if only_errors:
        if "error" not in combined:
            failures.append(f"[{level}] Expected 'error' in log output")
    else:
        if "crew_run" not in combined:
            failures.append(f"[{level}] Expected 'crew_run' in log output")
        if "error" not in combined:
            failures.append(f"[{level}] Expected 'error' in log output")
        if "agent_service" not in combined:
            failures.append(
                f"[{level}] Expected component 'agent_service' in log output"
            )
        if level == "DEBUG":
            if "traceback" not in combined:
                failures.append(
                    f"[{level}] DEBUG: expected 'traceback' in error log output"
                )
            if DEBUG_ONLY_TRACEBACK_SENTINEL not in combined:
                failures.append(
                    f"[{level}] DEBUG: expected traceback content ({DEBUG_ONLY_TRACEBACK_SENTINEL}) in log output"
                )
        elif level == "INFO":
            if DEBUG_ONLY_TRACEBACK_SENTINEL in combined:
                failures.append(
                    f"[{level}] INFO: traceback must not appear (expected only at DEBUG)"
                )

    if failures:
        for f in failures:
            print("FAIL:", f)
        return 1
    return 0


def main() -> int:
    if "--level" in sys.argv:
        level = os.environ.get("AI_INFRA_LOG_LEVEL", "INFO").upper()
        if level not in LOG_LEVELS:
            level = "INFO"
        return _run_single_level(level)

    print("Testing logging at all levels: DEBUG, INFO, WARNING, ERROR")
    print()
    results: list[tuple[str, int, str, str]] = []
    for level in LOG_LEVELS:
        env = {**os.environ, "AI_INFRA_LOG_LEVEL": level}
        pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join([_src] + ([pp] if pp else []))
        result = subprocess.run(
            [sys.executable, __file__, "--level", level],
            env=env,
            cwd=_repo_root,
            timeout=60,
            capture_output=True,
            text=True,
        )
        results.append(
            (level, result.returncode, result.stdout or "", result.stderr or "")
        )

    failed_levels = [lev for lev, code, _, _ in results if code != 0]
    passed_levels = [lev for lev, code, _, _ in results if code == 0]

    print("--- Logging summaries ---")
    for level, returncode, out, err in results:
        status = "FAILED" if returncode != 0 else "OK"
        print(f"\n[{level}] ({status})")
        if out:
            print(out.rstrip())
        if err:
            print(err.rstrip())

    print("\n" + "=" * 60)
    print("Overall stats")
    print("=" * 60)
    print(f"  Levels run:    {len(LOG_LEVELS)} ({', '.join(LOG_LEVELS)})")
    print(
        f"  Passed:       {len(passed_levels)} {tuple(passed_levels) if passed_levels else ''}"
    )
    print(
        f"  Failed:       {len(failed_levels)} {tuple(failed_levels) if failed_levels else '—'}"
    )
    print(
        f"  Success rate: {len(passed_levels)}/{len(LOG_LEVELS)} ({100 * len(passed_levels) // len(LOG_LEVELS)}%)"
    )
    print()

    for level, returncode, _, _ in results:
        print(f"  {level}: {'FAILED' if returncode != 0 else 'OK'}")

    if failed_levels:
        print()
        print("FAIL: One or more levels failed:", ", ".join(failed_levels))
        return 1
    print()
    print("All logging checks passed for all levels (DEBUG, INFO, WARNING, ERROR).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
