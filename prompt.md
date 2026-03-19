# Cursor Prompt Template: Generate My Agent From This Boilerplate

Copy everything below and paste into Cursor chat from the repository root.

---

## Prompt to Paste in Cursor

You are working inside the `ai-agent-boilerplate` repository.

Your goal is to transform this example into an initial working agent for my use case by updating business logic and API contracts in one end-to-end pass, while keeping shared infra/boilerplate patterns intact (AI Config validation, tracing, prompt sync toggle, runtime config gating, health/probes, and deployment structure).

### Inputs (fill placeholders before running)

#### 1) Crew-level description (what we want to achieve)
- **Agent/Product name:** `<AGENT_PRODUCT_NAME>`
- **One-line objective:** `<WHAT_THE_CREW_SHOULD_ACHIEVE>`
- **Primary user/problem:** `<WHO_USES_IT_AND_WHY>`
- **Expected output style:** `<JSON_SUMMARY|RECOMMENDATIONS|CLASSIFICATION|EXTRACTION|OTHER>`
- **Domain constraints:** `<TONE|COMPLIANCE|SAFETY|NO_HALLUCINATION_RULES|ETC>`

#### 2) Basic agents + tasks required
- **Agent definitions (minimum set):**
  - Agent 1: `<AGENT_1_NAME>` - role: `<ROLE>` - responsibility: `<RESPONSIBILITY>`
  - Agent 2: `<AGENT_2_NAME>` - role: `<ROLE>` - responsibility: `<RESPONSIBILITY>`
  - Agent N: `<AGENT_N_NAME>` - role: `<ROLE>` - responsibility: `<RESPONSIBILITY>`
- **Task definitions (minimum set):**
  - Task 1: `<TASK_1_NAME>` - purpose: `<PURPOSE>` - output: `<OUTPUT_TYPE>`
  - Task 2: `<TASK_2_NAME>` - purpose: `<PURPOSE>` - output: `<OUTPUT_TYPE>`
  - Task N: `<TASK_N_NAME>` - purpose: `<PURPOSE>` - output: `<OUTPUT_TYPE>`
- **Task flow:** `<SEQUENTIAL|HIERARCHICAL|MIXED>` with order `<TASK_ORDER>`

#### 3) API contract
- **Endpoint path to expose:** `<e.g. /my-use-case>`
- **Request fields (include types + required/optional):** `<REQUEST_SCHEMA_SPEC>`
- **Response fields (include types):** `<RESPONSE_SCHEMA_SPEC>`
- **WebSocket support needed?:** `<YES|NO>`
- **Kafka support needed?:** `<YES|NO>`

#### 4) Tools and integrations
- **Tools to use from existing repo (if any):** `<custom_tool|slack_tool|confluence|elastic|none>`
- **New tools needed:** `<TOOL_NAMES_AND_PURPOSE>`
- **External APIs/dependencies to call:** `<API_NAME_AND_USAGE>`

#### 5) Runtime toggles and config
- **Enable prompt management?:** `<YES|NO>`
- **Enable short-term memory?:** `<YES|NO>`
- **Enable DBs:** `sql=<YES|NO>, mongo=<YES|NO>, redis=<YES|NO>`
- **Enable endpoints:** `rest=<YES|NO>, websocket=<YES|NO>, kafka=<YES|NO>`

#### 6) Naming
- **Crew class name:** `<CREW_CLASS_NAME>`
- **Primary request model name:** `<REQUEST_MODEL_NAME>`
- **Primary response model name:** `<RESPONSE_MODEL_NAME>`
- **Primary operation name (for service logging):** `<OPERATION_NAME>`

---

### Required implementation tasks

Implement all of the following in one cohesive update:

1. Update `src/agent/crew.py`
   - Replace sample survey-specific models and crew logic with the provided agents/tasks.
   - Keep `BaseAICrew` inheritance pattern.
   - Keep `llm=self.llm` for all agents.
   - Ensure task outputs map to valid Pydantic models.

2. Update prompt/task configs
   - Rewrite `src/agent/config/agents.yaml` and `src/agent/config/tasks.yaml` to match new agent/task keys.
   - Ensure keys in YAML exactly match `@agent` and `@task` methods in `crew.py`.

3. Update API schemas in `src/agent/api/schemas.py`
   - Replace `SurveyDataRequest`/`SurveySummaryResponse` with the new request/response models.
   - Keep core platform fields required for AI config + tracing in request model:
     - `smtip_tid: str`
     - `smtip_feature: str`
     - `model: str`
     - `user_id: str`
     - `sesssion_id: str`
     - optional `tags`

4. Update service logic in `src/agent/api/agent_service.py`
   - Rename survey-specific functions to domain-specific names.
   - Build inputs from new request schema.
   - Keep runtime config loading and endpoint toggles intact.
   - Keep prompt sync behavior conditioned on `agent_runtime_config.prompt_management.enabled`.
   - Keep `run_with_tracing(...)` execution path.
   - Keep structured logging flow with operation name updated.

5. Update routes in `src/agent/api/routes.py`
   - Replace `/survey-summary` REST route with the new endpoint path.
   - Wire request/response models and service call to new names.
   - Keep tenant validation dependency and runtime endpoint gating.
   - If WebSocket is enabled, update WS route and payload handling for the new schema.
   - Update sample_curl.sh file to test the RestAPI endpoint

6. Update Kafka flow if enabled
   - Update `src/agent/api/kafka_pipeline.py` to use the new schema and service function names.
   - Keep robust error handling and response envelope format.

7. Update tool calls
   - Add/update tool wiring in crew agents where needed.
   - Reuse existing tools under `src/agent/tools/` when applicable.
   - If creating new tools, add them under `src/agent/tools/` with clear function signatures.

8. Update config pointers/constants if required
   - Update `src/agent/api/constants.py` only where naming/path changes are necessary.
   - Preserve existing shared paths and runtime behavior unless explicitly required.

9. Keep non-business boilerplate stable
   - Do not remove health/startup/live/ready endpoints.
   - Do not break AI Config validation flow.
   - Do not remove Langfuse tracing pathway.
   - Do not change installation scripts or CI/CD files unless required by naming consistency.

10. Validate consistency
   - Ensure all imports resolve.
   - Ensure renamed symbols are consistently updated across files.
   - Ensure schema <-> service <-> route <-> crew contract is aligned.

---

### Expected output format from Cursor

After making code changes, provide:

1. **What changed** (file-by-file concise summary)
2. **Open assumptions/placeholders still needing human input**
3. **How to test quickly** (one REST example, and WS/Kafka examples if enabled)
4. **Follow-up TODOs** for production hardening

---

### Important constraints

- Prefer minimal but working implementation over over-engineering.
- Keep code style aligned with existing repo patterns.
- Preserve common infra components from boilerplate; only replace business-specific logic.
- If any user input is ambiguous, choose sensible defaults and clearly document assumptions.
