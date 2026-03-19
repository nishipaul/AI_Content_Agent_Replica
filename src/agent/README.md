# Agent Framework

**Thin wrapper** on CrewAI’s `CrewBase`: adds Custom LLM init and optional observability. **No changes to CrewAI**—all CrewAI behavior (config injection, `@agent`/`@task`/`@crew`, `.crew()`, `.kickoff()`, streaming) works out of the box.

## Wrapper semantics

- **BaseAICrew extends `crewai.project.CrewBase`** and does not override any CrewAI methods.
- **Only adds:** (1) `__init__` sets `self.llm = CustomLLM(...)` so subclasses use `self.llm` in agents; (2) `run_with_tracing()` for Langfuse when running outside the API.
- **Unchanged:** `@CrewBase`, `agents_config`/`tasks_config`, `@agent`/`@task`/`@crew`, `.agents`/`.tasks`/`.crew()`, `.kickoff()`, streaming—all work as in plain CrewAI.

## Features

| Feature | Description |
|--------|-------------|
| **Custom LLM** | `BaseAICrew.__init__` sets `self.llm = CustomLLM(...)` (from `ai_infra_python_sdk.ai_infra.llm`). Use `self.llm` in your `@agent` methods as you would with CrewBase. |
| **Observability** | From **agent.api** routes, tracing is applied by the endpoint. For CLI/scripts, use `run_with_tracing(inputs, name="my-crew", tags=[...])`; it only wraps `crew().kickoff(inputs)`. |
| **API** | Specific routes (e.g. POST /api/v1/survey-summary) invoke your crew. Add or extend routes in `agent.api.routes` to expose new crews. |

## Config

- **`config/agents.yaml`** — Example agent config (role, goal, backstory). Copy or extend for your crew.
- **`config/tasks.yaml`** — Example task config (description, expected_output, agent). Use `{locale}`, `{survey_data}`, etc. for kickoff inputs.

CrewBase loads **agents_config** and **tasks_config** from your **package’s** `config/` directory (e.g. `agent/config/` for `SurveySummaryCrew`).

## Extending the base class

1. **Subclass `BaseAICrew`** and apply `@CrewBase` to your class.
2. **Put config** in your package: `config/agents.yaml`, `config/tasks.yaml`.
3. **Define agents and tasks** with `@agent` and `@task`, using `self.llm` and `self.agents_config` / `self.tasks_config`.
4. **Define the crew** with `@crew` returning `Crew(agents=self.agents, tasks=self.tasks, ...)`.

Example (see `agent/crew.py` for the full pattern):

```python
from typing import Any, Dict, List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from ai_infra_python_sdk.base_crew import BaseAICrew


@CrewBase
class MyCrew(BaseAICrew):
    agents_config: Dict[str, Any]   # from config/agents.yaml
    tasks_config: Dict[str, Any]    # from config/tasks.yaml

    @agent
    def my_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["my_agent"],
            verbose=True,
            llm=self.llm,
        )

    @task
    def my_task(self) -> Task:
        return Task(
            config=self.tasks_config["my_task"],
            agent=self.my_agent(),
        )

    @crew
    def crew(self, stream: bool = False) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            stream=stream,
        )
```

## Running the crew

- **From API**: Use existing routes (e.g. POST /api/v1/survey-summary) or add your own in agent.api.routes.
- **From CLI/script**: Instantiate your crew, then use `run_with_tracing(inputs, name="my-crew", tags=["my-crew"])` for Langfuse tracing, or `crew().kickoff(inputs=inputs)` without tracing.

## Package layout

```
src/
  agent/
    __init__.py          # re-exports from ai_infra_python_sdk.base_crew
    api/                 # FastAPI app, routes, schemas
    config/              # example agent config
    tools/               # CrewAI tools (Slack, Elasticsearch, Confluence, custom)
    README.md            # this file
```

Infrastructure (Custom LLM, observability, BaseAICrew, Vault, Redis, DB) is provided by **ai_infra_python_sdk**.
