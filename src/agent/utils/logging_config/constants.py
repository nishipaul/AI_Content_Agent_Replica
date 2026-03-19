"""Event phase, status, and log level constants for consistent vocabulary."""

EVENT_PHASE_START = "start"
EVENT_PHASE_END = "end"
STATUS_SUCCESS = "success"
STATUS_FAILURE = "failure"

# Placeholder for unset context (excluded from to_log_dict() so logs are JSON with only real values).
LOG_SENTINEL_UNSET = "-"

# Log level: set AI_INFRA_LOG_LEVEL in the environment to control output process-wide.
LOG_LEVEL_ENV_VAR = "AI_INFRA_LOG_LEVEL"
VALID_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")
DEFAULT_LOG_LEVEL = "INFO"
