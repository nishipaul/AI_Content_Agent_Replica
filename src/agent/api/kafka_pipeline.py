"""
Kafka pipeline: consume messages from one topic, run crew kickoff, produce results to another topic.

Runs on a separate thread when agent_runtime_config.endpoints.kafka_enabled is true in master_config.yaml.
Uses kafka-python. Message value = JSON (same shape as AgentDataRequest); output = JSON (AgentDataResponse-like).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import threading
import time
import uuid
from typing import Any, cast

import yaml

from agent.api.constants import (
    KAFKA_ACKS_DEFAULT,
    KAFKA_LINGER_MS_DEFAULT,
    KAFKA_REQUEST_REPLY_TIMEOUT_SECONDS,
    MASTER_CONFIG_PATH,
    SERVICE_ID,
)
from agent.utils.logging_config import get_logger_without_crew_context


def _kafka_bootstrap_servers() -> str:
    """Resolved Kafka bootstrap servers string (host:port) from env."""
    addr = (
        os.getenv("KAFKA_BOOTSTRAP_ADDRESS")
        or os.getenv("kafka_bootstrap_address")
        or ""
    ).strip()
    if addr:
        return addr
    url = (os.getenv("KAFKA_URL") or os.getenv("kafka_url") or "").strip()
    port = (os.getenv("KAFKA_PORT") or os.getenv("kafka_port") or "").strip()
    if url and port:
        return f"{url}:{port}"
    if url and ":" in url:
        return url
    return "localhost:9092"


logger = get_logger_without_crew_context("kafka_pipeline")


def _load_master_config() -> dict[str, Any]:
    with open(MASTER_CONFIG_PATH, "r") as f:
        return cast(dict[str, Any], yaml.safe_load(f))


def _is_kafka_enabled() -> bool:
    config = _load_master_config()
    return (
        config.get("agent_runtime_config", {})
        .get("endpoints", {})
        .get("kafka_enabled", False)
        is True
    )


def _make_ssl_context_no_verify():
    """SSL context that skips certificate verification (for AWS MSK / self-signed certs)."""
    import ssl

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _normalized_env_suffix(value: str) -> str:
    """Normalize arbitrary ids (agent/group) into ENV-safe suffix."""
    return re.sub(r"[^A-Z0-9]+", "_", value.strip().upper()).strip("_")


def _get_consumer_agent_id() -> str:
    """Resolve current consumer's agent_id from env/config."""
    agent_id = (
        os.getenv("KAFKA_CONSUMER_AGENT_ID")
        or _load_master_config().get("agent_registry_config", {}).get("agent_id")
        or SERVICE_ID
    )
    return str(agent_id).strip()


def _get_consumer_group_id(agent_id: str) -> str:
    """Resolve unique consumer group id for this agent."""
    return (
        os.getenv("KAFKA_GROUP_ID")
        or os.getenv(f"KAFKA_GROUP_ID_{_normalized_env_suffix(agent_id)}")
        or f"{agent_id}-consumer-group"
    )


def _get_max_poll_interval_ms(agent_id: str, group_id: str) -> int:
    """Resolve max_poll_interval_ms with optional group/agent overrides."""
    group_suffix = _normalized_env_suffix(group_id)
    agent_suffix = _normalized_env_suffix(agent_id)
    raw = (
        os.getenv(f"MAX_POLL_INTERVAL_MS_{group_suffix}")
        or os.getenv(f"MAX_POLL_INTERVAL_MS_{agent_suffix}")
        or os.getenv("MAX_POLL_INTERVAL_MS")
        or "600000"
    )
    try:
        return max(1000, int(raw))
    except ValueError:
        return 600000


def _get_processing_timeout_seconds(
    max_poll_interval_ms: int, agent_id: str, group_id: str
) -> int:
    """
    Resolve per-message processing timeout.
    Defaults to slightly below max_poll_interval_ms to reduce rebalance/commit failures.
    """
    group_suffix = _normalized_env_suffix(group_id)
    agent_suffix = _normalized_env_suffix(agent_id)
    raw = (
        os.getenv(f"KAFKA_PROCESS_TIMEOUT_SECONDS_{group_suffix}")
        or os.getenv(f"KAFKA_PROCESS_TIMEOUT_SECONDS_{agent_suffix}")
        or os.getenv("KAFKA_PROCESS_TIMEOUT_SECONDS")
    )
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return max(1, int(max_poll_interval_ms / 1000) - 5)


def _get_kafka_config(*, group_id: str, max_poll_interval_ms: int) -> dict[str, Any]:
    """Consumer config from env (SSL, bootstrap, group_id, etc.)."""
    security_protocol = os.getenv("SECURITY_PROTOCOL", "SSL")
    cfg = {
        "bootstrap_servers": _kafka_bootstrap_servers().split(","),
        "group_id": group_id,
        "enable_auto_commit": False,
        "auto_offset_reset": "latest",
        "security_protocol": security_protocol,
        "max_poll_interval_ms": max_poll_interval_ms,
        "max_poll_records": int(os.getenv("MAX_POLL_RECORDS", "1")),
    }
    if security_protocol == "SSL":
        cfg["ssl_check_hostname"] = False
        cfg["ssl_context"] = _make_ssl_context_no_verify()
    return cfg


def _get_kafka_producer_config() -> dict[str, Any]:
    """Producer config from env; matches notebook SSL setup."""
    security_protocol = os.getenv("SECURITY_PROTOCOL", "SSL")
    cfg = {
        "bootstrap_servers": _kafka_bootstrap_servers().split(","),
        "security_protocol": security_protocol,
        "linger_ms": KAFKA_LINGER_MS_DEFAULT,
        "acks": KAFKA_ACKS_DEFAULT,
    }
    if security_protocol == "SSL":
        cfg["ssl_check_hostname"] = False
        cfg["ssl_context"] = _make_ssl_context_no_verify()
    return cfg


def _parse_envelope(raw_value: bytes) -> tuple[str | None, str | None, dict[str, Any]]:
    """
    Parse JSON message envelope.
    Expected shape: {"agent_id":"...", "correlation_id":"...", "data":{...}}
    """
    decoded = json.loads(raw_value.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("Kafka message must be a JSON object")

    if "agent_id" not in decoded:
        raise ValueError("Kafka envelope must include 'agent_id'")
    if "data" not in decoded:
        raise ValueError("Kafka envelope must include 'data'")

    payload = decoded.get("data")
    if not isinstance(payload, dict):
        raise ValueError("Kafka envelope 'data' must be a JSON object")
    agent_id = decoded.get("agent_id")
    correlation_id = decoded.get("correlation_id")

    agent_id_normalized = str(agent_id).strip() if agent_id is not None else None
    if not agent_id_normalized:
        raise ValueError("Kafka envelope 'agent_id' must be a non-empty string")
    correlation_id_normalized = (
        str(correlation_id).strip() if correlation_id is not None else None
    )
    if correlation_id_normalized == "":
        correlation_id_normalized = None
    return agent_id_normalized, correlation_id_normalized, cast(dict[str, Any], payload)


def _build_envelope(
    agent_id: str, correlation_id: str | None, data: dict[str, Any]
) -> dict[str, Any]:
    """Build standardized Kafka envelope with metadata."""
    return {
        "agent_id": agent_id,
        "correlation_id": correlation_id,
        "data": data,
    }


async def _process_one_message_async(raw_value: bytes) -> dict[str, Any]:
    """Parse message, validate tenant and AI config, run crew, return response dict (for JSON produce)."""
    from agent.api.agent_service import build_agent_inputs, run_agentic_crew
    from agent.api.constants import DEFAULT_MODEL
    from agent.api.schemas import AgentDataRequest, AgentDataResponse
    from agent.api.tenant import tenant_exists

    _, _, payload = _parse_envelope(raw_value)
    request = AgentDataRequest.model_validate(payload)
    start = time.time()

    if not await tenant_exists(str(request.smtip_tid), str(request.smtip_feature)):
        raise ValueError(
            "Tenant not registered or agent not enabled for this tenant/feature"
        )

    crew_specific_fields = {
        k: v
        for k, v in payload.items()
        if k
        not in {"smtip_tid", "smtip_feature", "model", "user_id", "session_id", "tags"}
    }
    inputs = build_agent_inputs(
        smtip_tid=request.smtip_tid,
        smtip_feature=request.smtip_feature,
        model=request.model or DEFAULT_MODEL,
        user_id=request.user_id,
        session_id=request.session_id,
        tags=request.tags,
        reasoning_effort=request.reasoning_effort,
        **crew_specific_fields,
    )
    result = await run_agentic_crew(inputs)
    latency_seconds = round(time.time() - start, 3)

    content = result
    if result is not None and hasattr(result, "pydantic"):
        content = result.pydantic
    elif result is not None and hasattr(result, "raw"):
        content = result.raw

    result_dict: dict[str, Any] = AgentDataResponse(
        id=str(uuid.uuid4()),
        success=True,
        content=content,
        error=None,
        latency_seconds=latency_seconds,
    ).model_dump(mode="json")
    return result_dict


#######################################################################################################


def _run_consumer_loop() -> None:
    """Run Kafka consumer in this thread; process each message and produce to output topic."""
    from kafka import KafkaConsumer, KafkaProducer
    from kafka.errors import CommitFailedError, NoBrokersAvailable

    agent_id = _get_consumer_agent_id()
    print(f"Agent ID: {agent_id}")
    group_id = _get_consumer_group_id(agent_id)
    max_poll_interval_ms = _get_max_poll_interval_ms(agent_id, group_id)
    processing_timeout_seconds = _get_processing_timeout_seconds(
        max_poll_interval_ms=max_poll_interval_ms,
        agent_id=agent_id,
        group_id=group_id,
    )
    CONSUMER_CONFIG = _get_kafka_config(
        group_id=group_id,
        max_poll_interval_ms=max_poll_interval_ms,
    )
    PRODUCER_CONFIG = _get_kafka_producer_config()
    consumer_topic = os.getenv("CONSUMER_TOPIC", "survey-summary-requests")
    producer_topic = os.getenv("PRODUCER_TOPIC", "survey-summary-results")
    try:
        consumer = KafkaConsumer(
            consumer_topic,
            **CONSUMER_CONFIG,
            value_deserializer=lambda v: v,
        )
        producer = KafkaProducer(
            **PRODUCER_CONFIG,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
    except NoBrokersAvailable:
        logger.info(
            "kafka_pipeline_not_started_brokers_unreachable",
            message="For local dev without Kafka keep kafka_enabled: false in master_config.",
        )
        return
    except Exception as e:
        logger.error(
            "kafka_pipeline_create_failed",
            error=str(e),
            exc_info=True,
        )
        return

    def _safe_commit() -> None:
        try:
            consumer.commit()
        except CommitFailedError as e:
            logger.warning(
                "kafka_offset_commit_failed",
                error=str(e),
                message="Message was still produced. Consider increasing MAX_POLL_INTERVAL_MS.",
            )

    worker_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(worker_loop)

    def _run_with_timeout(raw_value: bytes) -> dict[str, Any]:
        return worker_loop.run_until_complete(
            asyncio.wait_for(
                _process_one_message_async(raw_value),
                timeout=processing_timeout_seconds,
            )
        )

    try:
        for message in consumer:
            try:
                message_agent_id, correlation_id, _ = _parse_envelope(message.value)

                # Shared topic: each consumer group processes only its own agent_id.
                if message_agent_id != agent_id:
                    _safe_commit()
                    continue

                result = _run_with_timeout(message.value)
                producer.send(
                    producer_topic,
                    value=_build_envelope(
                        agent_id=agent_id,
                        correlation_id=correlation_id,
                        data=result,
                    ),
                )
                producer.flush()
                _safe_commit()
            except asyncio.TimeoutError:
                error_payload = {
                    "success": False,
                    "content": None,
                    "error": (
                        f"Agent execution exceeded timeout of {processing_timeout_seconds}s "
                        f"(group_id={group_id}, max_poll_interval_ms={max_poll_interval_ms})"
                    ),
                    "latency_seconds": None,
                }
                try:
                    message_agent_id, correlation_id, _ = _parse_envelope(message.value)
                    producer.send(
                        producer_topic,
                        value=_build_envelope(
                            agent_id=message_agent_id or agent_id,
                            correlation_id=correlation_id,
                            data=error_payload,
                        ),
                    )
                    producer.flush()
                except Exception as send_err:
                    logger.error(
                        "kafka_pipeline_send_timeout_error_result_failed",
                        error=str(send_err),
                        exc_info=True,
                    )
                finally:
                    _safe_commit()
            except Exception as e:
                logger.error(
                    "kafka_pipeline_message_error",
                    error=str(e),
                    exc_info=True,
                )
                error_payload = {
                    "success": False,
                    "content": None,
                    "error": str(e),
                    "latency_seconds": None,
                }
                try:
                    message_agent_id, correlation_id, _ = _parse_envelope(message.value)
                    producer.send(
                        producer_topic,
                        value=_build_envelope(
                            agent_id=message_agent_id or agent_id,
                            correlation_id=correlation_id,
                            data=error_payload,
                        ),
                    )
                    producer.flush()
                except Exception as send_err:
                    logger.error(
                        "kafka_pipeline_send_error_result_failed",
                        error=str(send_err),
                        exc_info=True,
                    )
                finally:
                    _safe_commit()
    finally:
        try:
            consumer.close()
            producer.close()
        except Exception:
            pass
        try:
            worker_loop.close()
        except Exception:
            pass


def request_reply_via_kafka_sync(
    request_payload: dict[str, Any],
    timeout_seconds: int = KAFKA_REQUEST_REPLY_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    Produce a survey-summary request to the consumer topic with a correlation_id,
    wait for the pipeline to process and produce the response to the producer topic,
    then return the response dict. Raises TimeoutError if no matching response in time.
    Blocking; run from async route via asyncio.to_thread.
    """
    from kafka import KafkaConsumer, KafkaProducer
    from kafka.errors import NoBrokersAvailable

    correlation_id = str(uuid.uuid4())
    consumer_topic = os.getenv("CONSUMER_TOPIC", "survey-summary-requests")
    producer_topic = os.getenv("PRODUCER_TOPIC", "survey-summary-results")
    request_agent_id = _get_consumer_agent_id()
    payload = _build_envelope(
        agent_id=request_agent_id,
        correlation_id=correlation_id,
        data=request_payload,
    )

    consumer_config = {
        **_get_kafka_config(
            group_id=f"kafka-http-reply-{correlation_id}",
            max_poll_interval_ms=120000,
        ),
        "group_id": f"kafka-http-reply-{correlation_id}",
        "auto_offset_reset": "latest",
    }
    producer_config = _get_kafka_producer_config()
    try:
        consumer = KafkaConsumer(
            producer_topic,
            **consumer_config,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")) if v else None,
        )
        producer = KafkaProducer(
            **producer_config,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
    except NoBrokersAvailable as e:
        raise RuntimeError(
            "Kafka brokers not reachable; cannot run request-reply. "
            "Check bootstrap servers or set kafka_enabled=false in master_config."
        ) from e
    except Exception as e:
        raise RuntimeError(
            f"Kafka request-reply failed to create consumer/producer: {e}"
        ) from e

    try:
        producer.send(consumer_topic, value=payload)
        producer.flush()
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            batch = consumer.poll(timeout_ms=2000)
            for _topic_partition, records in batch.items():
                for rec in records:
                    if not rec.value:
                        continue
                    if rec.value.get("correlation_id") != correlation_id:
                        continue
                    if rec.value.get("agent_id") != request_agent_id:
                        continue
                    response_payload = rec.value.get("data")
                    if isinstance(response_payload, dict):
                        return response_payload
        raise TimeoutError(
            f"No response from Kafka pipeline within {timeout_seconds}s (correlation_id={correlation_id})"
        )
    finally:
        try:
            consumer.close()
            producer.close()
        except Exception:
            pass


def start_kafka_pipeline_thread() -> threading.Thread | None:
    """
    If kafka_enabled in master_config, start the Kafka consumer loop in a daemon thread.
    Returns the thread if started, None if Kafka is disabled.
    """
    if not _is_kafka_enabled():
        logger.info(
            "kafka_pipeline_disabled", message="kafka_enabled=false in master_config"
        )
        return None
    thread = threading.Thread(
        target=_run_consumer_loop, name="kafka-pipeline", daemon=True
    )
    thread.start()
    logger.info("kafka_pipeline_thread_started")
    return thread


if __name__ == "__main__":
    print("Run the API with: uv run run_api  (or uvicorn agent.api:app --reload)")
