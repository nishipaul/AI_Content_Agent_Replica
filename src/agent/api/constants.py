"""
Constants and path definitions for the API layer.

All path and default-value constants used across the api folder live here.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from agent.utils.paths import BASE_DIR

# ----- Config file paths -----

MASTER_CONFIG_PATH: Path = BASE_DIR.parent / "master_config.yaml"  # Constant
AGENTS_CONFIG_PATH: Path = BASE_DIR / "agent/config/agents.yaml"  # Constant
TASKS_CONFIG_PATH: Path = BASE_DIR / "agent/config/tasks.yaml"  # Constant
PROMPT_CONFIG_PATH: Path = BASE_DIR.parent / "master_config.yaml"  # Constant

# ----- API / agent config defaults -----

AI_CONFIG_API_BASE_URL_DEFAULT: str = os.getenv(
    "AI_CONFIG_API_BASE_URL", "https://api-be.dev.simpplr.xyz"
)  # Change in env if needed, else will be https://api-be.dev.simpplr.xyz
ROUTER_PREFIX: str = (
    "/v1/ai-content-agent"  # Change the router prefix here if you need to
)
DOCS_PREFIX: str = (
    "ai-content-agent"  # Change the docs prefix here if you need to
)
DEFAULT_MODEL: str = "auto-route"  # Constant
DEFAULT_LLM_API: str = "completions"  # Either responses or completions
DEFAULT_MAX_OUTPUT_TOKENS: int | None = None  # Constant
DEFAULT_AGENT_NAME: str = "agent"  # Change as per need
DEFAULT_ENVIRONMENT: str = "dev"  # Change as per need

# ----- Kafka defaults -----

KAFKA_CONSUMER_TOPIC_DEFAULT: str = "Sample_AI_Agent_Topic_Dev"
KAFKA_PRODUCER_TOPIC_DEFAULT: str = "Sample_AI_Agent_Topic_2_Dev"
KAFKA_GROUP_ID_DEFAULT: str = "Sample_AI_Agent_Topic_Dev-crew-consumer"
KAFKA_BOOTSTRAP_SERVERS_DEFAULT: str = "localhost:9092"
KAFKA_SECURITY_PROTOCOL_DEFAULT: str = "SSL"
KAFKA_MAX_POLL_INTERVAL_MS_DEFAULT: int = 600_000
KAFKA_MAX_POLL_RECORDS_DEFAULT: int = 1
KAFKA_LINGER_MS_DEFAULT: int = 20
KAFKA_ACKS_DEFAULT: str = "all"
KAFKA_REQUEST_REPLY_TIMEOUT_SECONDS: int = 120


# ----- Kafka for Traces -----

KAFKA_ENABLED: bool = (
    os.getenv("KAFKA_ENABLED", "True").lower() == "true"
)  # Change in env if needed, else will be True
KAFKA_TRACES_TOPIC: str = os.getenv(
    "KAFKA_TRACES_TOPIC", "AI_Trace_Ingestion_Event_Dev"
)  # Change in env if needed, else will go to AI_Trace_Ingestion_Event_Dev topic


# ----- Master config Details for the agent - Not to be changed -----

with open(MASTER_CONFIG_PATH, "r") as file:
    master_config = yaml.safe_load(file)
    agent_runtime_config = master_config["agent_runtime_config"]
    agent_prompt_config = master_config["agent_prompt_config"]
    agent_registry_config = master_config["agent_registry_config"]

# ----- Environment Details for the agent-----

ENVIRONMENT = os.getenv(
    "ENVIRONMENT", "dev"
)  # Change in env if needed, else will be dev
REGION = os.getenv(
    "AWS_DEFAULT_REGION", ""
)  # Change in env if needed, else will be empty
TRACE_TYPE = os.getenv("TRACE_TYPE", "app")  # Change in env if needed, else will be app
APPLICATION_NAME = (
    "ai-content-agent"  # Change application name here if you need to
)


# ----- Service Details for the agent from the master config - Not to be changed here, change in master_config.yaml if needed -----

SERVICE_ID = agent_registry_config["agent_id"]
SERVICE_NAME = agent_registry_config["name"]
SERVICE_DESCRIPTION = agent_registry_config["description"]
SERVICE_TEAM = agent_registry_config["owner"]["team"]
SERVICE_TOOLS = agent_registry_config["tools"]
SERVICE_URL = agent_registry_config["endpoints"]["dev"]
SERVICE_FRAMEWORK = agent_registry_config["framework"]

# ----- Agent Names and Task Names for the agent from the master config - Not to be changed here, change in master_config.yaml if needed -----

AGENT_NAMES = [
    list(a.keys())[0]
    for a in agent_prompt_config.get("Agents", [])
    if isinstance(a, dict)
]
TASK_NAMES = [
    list(t.keys())[0]
    for t in agent_prompt_config.get("Tasks", [])
    if isinstance(t, dict)
]

try:
    USE_CREWAI_EXTERNAL_MEMORY = bool(agent_runtime_config["memory"]["short_term"])
except Exception:
    USE_CREWAI_EXTERNAL_MEMORY = False


# ----- Common Service Arguments for the agent to be used in the routes trace - NOT TO BE CHANGED-----
_COMMON_SERVICE_KWARGS = dict(
    application_name=APPLICATION_NAME,
    trace_type=TRACE_TYPE,
    service_id=SERVICE_ID,
    service_name=SERVICE_NAME,
    service_description=SERVICE_DESCRIPTION,
    service_framework=SERVICE_FRAMEWORK,
    service_tools=SERVICE_TOOLS,
    service_url=SERVICE_URL,
    service_team=SERVICE_TEAM,
    agent_names=AGENT_NAMES,
    task_names=TASK_NAMES,
    region=REGION,
    environment=ENVIRONMENT,
)


# --------- LLM Endpoints - Change in env if needed, else will be None ---------

LLM_COMPLETIONS_ENDPOINT = os.getenv("LLM_ENDPOINT", None)
LLM_RESPONSES_ENDPOINT = os.getenv("LLM_RESPONSES_ENDPOINT", None)
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_OUTPUT_TOKENS: int | None = (
    int(val)
    if (val := os.getenv("LLM_MAX_OUTPUT_TOKENS"))
    else DEFAULT_MAX_OUTPUT_TOKENS
)
LLM_GATEWAY_TIMEOUT: int | None = (
    int(val) if (val := os.getenv("LLM_GATEWAY_TIMEOUT")) else None
)
LLM_CONTEXT_WINDOW_SIZE: int | None = (
    int(val) if (val := os.getenv("LLM_CONTEXT_WINDOW_SIZE")) else None
)
LLM_RETRIES: int | None = int(val) if (val := os.getenv("LLM_RETRIES")) else None


# ------ Overall observability defaults -----

ENABLE_OBSERVABILITY: bool = (
    os.getenv("ENABLE_OBSERVABILITY", "True").lower() == "true"
)  # Change in env if needed, else will be True
