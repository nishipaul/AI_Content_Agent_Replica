# Creating Your Own Crew: Complete Guide

This guide covers everything you need to customize this boilerplate for your own AI agent, from core business logic to deployment and infrastructure integration.

---

## Part 1: Core Customization (What to Change and Why)

### Overview

This boilerplate uses a **generic architecture** where most infrastructure code (API, tracing, database connectors, Kafka) works for any crew. You only customize:
1. **Business logic** (agents, tasks, output models)
2. **API contract** (input/output schemas, endpoint paths)
3. **Configuration** (agent identity, runtime toggles)

---

### 1. Define Your Output Models

**File:** `src/agent/crew.py`

**Why:** Output models define the structured data your crew returns. This is specific to your use case.

**What to change:**
- Replace example Pydantic models (`Insight`, `SurveySummaryWithComments`) with your own
- Rename crew class from `BoilerplateCrew` to match your domain (Not necessary but is a good practice)
- Keep `__init__` unchanged (inherits from `BaseAICrew` with standard parameters)

**Reason:** The SDK expects structured outputs. Your models shape what the LLM produces.

---

### 2. Define Your Agent

**File:** `src/agent/crew.py`

**Why:** Agents have specific roles, goals, and expertise. Your agent needs a persona matching your task.

**What to change:**
- Rename the `@agent` method (e.g., `survey_analyst` → `document_analyst`)
- Update the config key to match your agent name in `agents.yaml`
- Keep `llm=self.llm` unchanged (uses SDK-managed LLM)

**Reason:** The agent's identity drives its behavior. The config key links code to YAML definitions.

---

### 3. Define Your Task

**File:** `src/agent/crew.py`

**Why:** Tasks define what the agent should accomplish. This is your core business logic.

**What to change:**
- Rename the `@task` method (e.g., `analysis_task` → `summarization_task`)
- Update config key to match your task in `tasks.yaml`
- Set `output_pydantic` to your output model from Step 1

**Reason:** Tasks orchestrate agent work. The output model ensures structured, validated results.

---

### 4. Configure Agent Details

**File:** `src/agent/config/agents.yaml`

**Why:** This YAML defines your agent's personality, expertise, and context.

**What to change:**
- Replace the agent key name
- Rewrite `role`, `goal`, `backstory` for your domain
- Update input variable placeholders (e.g., `{locale}`, `{survey_data}` → `{document_text}`)

**Reason:** These prompts guide the LLM's behavior. Variables let you inject dynamic content at runtime.

---

### 5. Configure Task Instructions

**File:** `src/agent/config/tasks.yaml`

**Why:** Task descriptions tell the agent exactly what to do and how.

**What to change:**
- Replace task key name
- Rewrite `description` with your instructions
- Update variable placeholders to match your input data
- Define clear `expected_output`
- Update `agent` reference to your agent name

**Reason:** Clear instructions = better results. Variables connect your API inputs to agent prompts.

---

### 6. Update Request Schema

**File:** `src/agent/api/schemas.py`

**Why:** Your API accepts different input data than the example.

**What to change:**
- In `AgentDataRequest`: replace example fields (`locale`, `survey_data`) with yours
- Keep infrastructure fields unchanged (`smtip_tid`, `smtip_feature`, `model`, `user_id`, `session_id`, `tags`, `reasoning_effort`)
- Update import to your output model
- In `AgentDataResponse`: change `content` type to your output model

**Reason:** Infrastructure fields enable tracing, tenant validation, and LLM routing. Your custom fields carry business data.

---

### 7. Update Agent Service Import

**File:** `src/agent/api/agent_service.py`

**Why:** The service needs to instantiate your crew class.

**What to change:**
- Import your crew class instead of `BoilerplateCrew`
- Update the instantiation line to use your class name

**Reason:** This is the only code coupling. Everything else is generic and passes through `**kwargs`.

---

### 8. Update API Endpoints

**File:** `src/agent/api/routes.py`

**Why:** Your API endpoints should reflect your service's purpose.

**What to change:**
- REST endpoint path (e.g., `/survey-summary` → `/document-summary`)
- WebSocket endpoint path (if enabled)
- WebSocket handler: pass your request fields to `generate_response()`

**Reason:** Clear endpoint names improve API discoverability. The auto-extraction handles REST; WebSocket needs explicit field passing.

---

### 9. Update Master Configuration

**File:** `master_config.yaml`

**Why:** This file registers your agent's identity and controls runtime behavior.

**What to change:**
- `agent_registry_config`: identity (agent_id, name, description, tags, capabilities, owner info)
- `agent_prompt_config`: map agent/task names to prompt versions

**Reason:** Registry config makes your agent discoverable. Prompt config enables Langfuse integration when enabled.

---

### 10. Update Environment Variables

**File:** `.env`

**Why:** Runtime needs to know your agent's name for logging and tracing.

**What to change:**
- `AGENT_NAME` value

**Reason:** Used in trace names, logs, and operational context.

---

### Why Other Files Don't Change

**These files are generic and work for any crew:**

- **`src/agent/api/constants.py`**: Infrastructure constants (LLM config, Kafka defaults)
- **`src/agent/api/tenant.py`**: Tenant validation logic (reusable)
- **`src/agent/api/exceptions.py`**: Error handling (standard)
- **`src/agent/api/agent_service.py`**: Generic crew orchestration (uses `**kwargs` for flexibility)
- **`src/agent/api/kafka_pipeline.py`**: Auto-extracts crew-specific fields from messages
- **`src/agent/utils/`**: Logging, paths, tracing (infrastructure)
- **`src/agent/db_connections/`**: Database connectors (reusable)

**Design principle:** Separate infrastructure (reusable) from business logic (customizable).

---

## Part 2: Optional Enhancements

### Adding Custom Tools

**When:** Your agent needs to call APIs, query databases, or perform actions.

**Where:** `src/agent/tools/` (create new tool class)

**How:** Inherit from `BaseTool`, define schema, implement `_run()`, pass to agent via `tools=[...]`

**Example:**
```python
from agent.tools.custom_tool import MyCustomTool

@agent
def document_analyst(self) -> Agent:
    return Agent(
        config=self.agents_config["document_analyst"],
        llm=self.llm,
        tools=[MyCustomTool()],  # Add your tools here
    )
```

**Why:** Tools extend agent capabilities beyond text generation.

---

### Database Connections

**When:** Your crew needs to read/write persistent data.

**Where:** `src/agent/db_connections/` (connectors already available)

**How:** Import and use `get_mongo_connector()`, `get_redis_connector()`, or `get_sql_connector()`

**Example:**
```python
from agent.db_connections.get_mongo_connector import get_mongo_connector

db = get_mongo_connector()
collection = db["my_collection"]
```

**Why:** Pre-built connectors handle authentication, pooling, and error handling.

---

### Enabling/Disabling Endpoints

**When:** You don't need all interfaces (REST, WebSocket, Kafka).

**Where:** `master_config.yaml` → `agent_runtime_config.endpoints`

**Example:**
```yaml
agent_runtime_config:
  endpoints:
    rest_api_enabled: true   # Enable/disable REST API
    kafka_enabled: true      # Enable/disable Kafka consumer
    websocket_enabled: true  # Enable/disable WebSocket
```

**Why:** Toggle features without code changes. Reduces attack surface and resource usage.

---

### Short-term Memory

**When:** Your crew needs context across multiple turns in a session.

**Where:** `master_config.yaml`

**Example:**
```yaml
agent_registry_config:
  memory_config:
    short_term: true   # Enable in registry
    long_term: true

agent_runtime_config:
  memory:
    short_term: true   # Enable at runtime
```

**Why:** CrewAI external memory (Redis-backed) enables stateful conversations.

**Testing:** Use `scripts/test_memory.py` to verify memory persistence.

---

### Kafka Integration

**When:** Your crew consumes from event streams instead of REST.

**Where:** Set environment variables

**Example:**
```bash
CONSUMER_TOPIC=your-requests-topic
PRODUCER_TOPIC=your-results-topic
```

**Why:** Kafka pipeline auto-extracts crew fields. No code changes needed.

---

## Part 3: Deployment & Infrastructure

### Helm Values Configuration

Update service identity across all environment files:
- `helm-values/values.yaml` (base)
- `helm-values/dev-values.yaml`
- `helm-values/perf-values.yaml`
- `helm-values/release-values.yaml`

Ensure consistency with:
- `AGENT_NAME` in `.env`
- `agent_id` in `master_config.yaml`
- `ROUTER_PREFIX` in `src/agent/api/constants.py`

**Why:** Kubernetes deployments, service discovery, and routing depend on these matching.

---

### AI Config Service Integration

The boilerplate validates every request against AI Config to check:
- Tenant exists and is enabled
- Feature flag allows this agent for this tenant
- Model routing configuration

**No changes needed** - validation is automatic via `smtip_tid` and `smtip_feature` in requests.

**Override base URL** if needed:
```bash
AI_CONFIG_API_BASE_URL=https://your-ai-config-url.com
```

---

### Vault Integration

Secrets are fetched from AWS Secrets Manager using vault paths:

**Environment variables:**
```bash
AWS_SM_VAULT_CONFIG=vault/environment/orion
AWS_DEFAULT_REGION=us-west-2
AWS_PROFILE=your-aws-profile

SQL_VAULT_PATH=path/to/sql/credentials
MONGO_VAULT_PATH=path/to/mongo/credentials
REDIS_VAULT_PATH=path/to/redis/credentials
LANGFUSE_VAULT_PATH=path/to/langfuse/credentials
```

**Why:** Never hardcode credentials. Connectors automatically fetch from vault.

---

### Observability & Tracing

Tracing is **enabled by default** via:
- Langfuse for crew/task/agent traces
- OpenInference for span capture
- Kafka traces sent to ingestion topic

**Configuration:**
```yaml
# master_config.yaml
agent_runtime_config:
  prompt_management:
    enabled: true  # Syncs prompts from Langfuse
```

```bash
# .env
ENABLE_OBSERVABILITY=true
KAFKA_ENABLED=true
KAFKA_TRACES_TOPIC=AI_Trace_Ingestion_Event_Dev
```

**Disable for local testing:**
```bash
ENABLE_OBSERVABILITY=false
```

---

### Prompt Management with Langfuse

**When to enable:** After your prompts stabilize and you want version control.

**Setup:**
1. Create prompts in Langfuse UI matching your agent/task names
2. Update `agent_prompt_config` in `master_config.yaml`:
   ```yaml
   agent_prompt_config:
     Agents:
       - your_agent_name:
           name: your_prompt_name_in_langfuse
           Labels: [agent_your_agent_name]
           Version: [v1]
           Tags: [your-tag]
     Tasks:
       - your_task_name:
           name: your_prompt_name_in_langfuse
           Labels: [task_your_task_name]
           Version: [v1]
           Tags: [your-tag]
   ```
3. Set `prompt_management.enabled: true`
4. Use `src/agent/config/write_prompts_to_langfuse.py` to bulk-upload local YAML to Langfuse

**Why:** Centralized prompt versioning, A/B testing, and multi-environment management.

---

### Kafka Consumer Configuration

**When to use:** Asynchronous processing, event-driven architecture, high-throughput scenarios.

**Configuration:**
```bash
# .env
KAFKA_BOOTSTRAP_ADDRESS=your-kafka-broker:9093
CONSUMER_TOPIC=your-agent-requests-topic
PRODUCER_TOPIC=your-agent-results-topic
KAFKA_GROUP_ID=your-agent-consumer-group
SECURITY_PROTOCOL=SSL
MAX_POLL_INTERVAL_MS=600000
MAX_POLL_RECORDS=1
```

**Enable in runtime:**
```yaml
# master_config.yaml
agent_runtime_config:
  endpoints:
    kafka_enabled: true
```

**Message format:** Same as REST request body. Pipeline auto-extracts crew-specific fields.

**Why:** Kafka decouples producers from consumers, enables retries, and scales horizontally.

---

### Custom LLM Endpoints

Override default LLM routing:
```bash
# .env
LLM_ENDPOINT=https://your-llm-gateway.com/completions
LLM_RESPONSES_ENDPOINT=https://your-llm-gateway.com/responses
LLM_TEMPERATURE=0.7
LLM_MAX_OUTPUT_TOKENS=4096
LLM_GATEWAY_TIMEOUT=120
LLM_CONTEXT_WINDOW_SIZE=128000
LLM_RETRIES=3
```

**Why:** Support different LLM providers, internal gateways, or custom routing logic.

---

## Part 4: Testing & Validation

### Memory Testing
```bash
python scripts/test_memory.py
```
Validates short-term memory storage and retrieval.

### Local Crew Execution
```bash
python -m agent.main
```
Runs crew with sample inputs (no API server).

### API Testing
See `scripts/test_survey_summary_rest.py` and `scripts/test_survey_summary_ws.py` for examples.

---

## Part 5: Security & Performance

### Tenant Validation

Every request is validated against AI Config. **Do not disable** this in production:
- Prevents unauthorized access
- Enforces feature flags
- Tracks usage per tenant

### Header Requirements

All requests must include:
- `x-smtip-tid`: Tenant ID
- `x-smtip-feature`: Feature identifier

These are mapped from request body fields automatically.

---

### Performance Tuning

**Kafka Settings:**
Adjust based on message volume:
```bash
MAX_POLL_INTERVAL_MS=600000  # Max processing time per message
MAX_POLL_RECORDS=1           # Messages per poll (keep at 1 for long-running crews)
```

**LLM Timeouts:**
Increase for slow models or long tasks:
```bash
LLM_GATEWAY_TIMEOUT=300  # 5 minutes
```

**Memory Trade-offs:**
Short-term memory adds latency (Redis lookups). Disable if not needed:
```yaml
agent_runtime_config:
  memory:
    short_term: false
```

---

## Part 6: Deployment Checklists

### Pre-Deployment Checklist

Before deploying to production:

**Core Customization:**
- [ ] All 10 required changes completed (Part 1)
- [ ] Output models match your domain
- [ ] Agent/task YAML reflects your use case
- [ ] API schemas accept your input data
- [ ] Endpoint paths renamed appropriately
- [ ] `master_config.yaml` identity updated
- [ ] `.env` has correct `AGENT_NAME`

**Infrastructure:**
- [ ] Helm values updated for all environments
- [ ] Vault paths configured and tested
- [ ] AI Config tenant registration complete
- [ ] Observability validated (traces appear in Langfuse)
- [ ] Kafka topics created and accessible (if enabled)
- [ ] Memory tested (if enabled)

**Quality:**
- [ ] Load testing completed
- [ ] Error handling verified
- [ ] Logging levels appropriate for environment
- [ ] Health endpoints responding (`/v1/health`, `/v1/ready`)
- [ ] Unnecessary endpoints disabled
- [ ] Tools added if needed
- [ ] Tests updated (if applicable)

---

## Part 7: Troubleshooting

### Tracing Not Appearing
- Check `ENABLE_OBSERVABILITY=true`
- Verify Langfuse vault path and credentials
- Check Kafka traces topic is reachable

### Kafka Consumer Not Starting
- Verify `kafka_enabled: true` in `master_config.yaml`
- Check bootstrap servers reachable
- Validate SSL certificates if using SSL protocol

### Memory Not Persisting
- Check Redis vault path and connection
- Verify `short_term: true` in both config sections
- Run `scripts/test_memory.py` to diagnose

### Prompt Sync Failing
- Verify Langfuse credentials in vault
- Check prompt names match `agent_prompt_config`
- Ensure prompt versions exist in Langfuse

### Tenant Validation Errors
- Verify tenant is registered in AI Config
- Check feature flag is enabled for this tenant
- Confirm `smtip_tid` and `smtip_feature` are correct

---

## Part 8: Key Design Decisions

1. **SERVICE_ID replaces AGENT_ID**: Single source of truth from `master_config.yaml`
2. **Auto-field extraction**: REST routes and Kafka pipeline dynamically extract crew-specific fields
3. **YAML-driven prompts**: Agents and tasks defined in config files, not hardcoded
4. **Optional Langfuse sync**: Enable prompt management when ready
5. **Infrastructure/business separation**: Customize business logic, reuse infrastructure

---

## Part 9: Additional Resources

- **Architecture docs:** See `src/agent/README.md`
- **Testing guide:** See `tests/README.md`
- **Deployment pipeline:** See `.github/workflows/`
- **Scripts documentation:** See `scripts/README.md`

---

## Quick Reference: Customization Order

For fastest adoption with minimal breakage:

1. Update `master_config.yaml` identity + runtime toggles
2. Update schema models and API route contract
3. Replace crew logic and local YAML prompts/tasks
4. Validate REST path first; then WebSocket/Kafka (if needed)
5. Enable Langfuse prompt management after prompts stabilize
6. Finalize Helm values and registry metadata for deployment
