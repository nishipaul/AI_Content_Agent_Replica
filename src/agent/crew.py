import os
os.environ["CREWAI_LOG_LEVEL"] = "ERROR"
os.environ["CREWAI_TRACING_ENABLED"] = "false"

# Modify according to your crew

from typing import Any, Dict, List  # noqa: E402

from ai_infra_python_sdk_core.base_crew import (  # noqa: E402; type: ignore[import-untyped]
    BaseAICrew,
)
from crewai import Agent, Crew, Process, Task  # noqa: E402
from crewai.agents.agent_builder.base_agent import BaseAgent  # noqa: E402
from crewai.project import CrewBase, agent, crew, task  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

load_dotenv()


### FOR CHAT SUMMARISATION

class ChatMessage(BaseModel):
    """Single chat message in the conversation"""

    message_id: str = Field(..., description="Unique identifier for the message")
    sender_name: str = Field(..., description="Name of the person who sent the message")
    timestamp: str = Field(..., description="When the message was sent (ISO 8601)")
    text: str = Field(..., description="The message content")
    replied_to: str | None = Field(
        None, description="The message_id of the message this is a reply to"
    )


class ChatSummaryPayload(BaseModel):
    """Structured output schema for LLM chat summarization"""

    summary: str = Field(
        ..., description="Concise paragraph summary of the conversation"
    )



@CrewBase
class ChatSummariser(BaseAICrew):
    """Chat summariser crew: extends BaseAICrew (Custom LLM, observability, API-ready)."""
    
    agents_config = 'config/chat_summariser_agents.yaml'
    tasks_config = 'config/chat_summariser_tasks.yaml'

    def __init__(
        self,
        smtip_tid: str,
        smtip_feature: str,
        model: str,
        user_id: str,
        session_id: str,
        service_id: str,
        service_name: str,
        *,
        agent_id: str = "default",
        api: str = "completions",
        completions_endpoint: str | None = None,
        responses_endpoint: str | None = None,
        temperature: float | None = 0.7,
        max_output_tokens: int | None = None,
        reasoning_effort: str | None = None,
        instructions: str | None = None,
        trace_name: str = "crew-run",
        enable_observability: bool = True,
        use_crewai_external_memory: bool = False,
        storage_factory: Any = None,
        llm_gateway_timeout: int | None = None,
        context_window_size: int | None = None,
        retries: int | None = None,
    ):
        # Keep this BaseAICrew.__init__ as is - no changes needed
        BaseAICrew.__init__(
            self,
            smtip_tid=smtip_tid,
            smtip_feature=smtip_feature,
            model=model,
            user_id=user_id,
            session_id=session_id,
            service_id=service_id,
            service_name=service_name,
            agent_id=agent_id,
            api=api,
            completions_endpoint=completions_endpoint,
            responses_endpoint=responses_endpoint,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            reasoning_effort=reasoning_effort,
            instructions=instructions,
            trace_name=trace_name,
            enable_observability=enable_observability,
            use_crewai_external_memory=use_crewai_external_memory,
            storage_factory=storage_factory,
            llm_gateway_timeout=llm_gateway_timeout,
            context_window_size=context_window_size,
            retries=retries,
        )

    agents: List[BaseAgent]
    tasks: List[Task]
    agents_config: Dict[str, Any]
    tasks_config: Dict[str, Any]

    @agent
    def chat_summariser(self) -> Agent:
        return Agent(
            config=self.agents_config["chat_summariser"],
            verbose=True,
            llm=self.llm,
        )

    @task
    def summarisation_task(self) -> Task:
        return Task(
            config=self.tasks_config["summarisation_task"],
            output_pydantic=ChatSummaryPayload,
            # human_input = True,
        )


    @crew
    def crew(
        self,
        stream: bool = False,
        external_memory: Any = None,
    ) -> Crew:
        """Creates the SurveySummaryCrew crew.

        Args:
            stream: If True, kickoff() returns a CrewStreamingOutput you can iterate
                    for real-time chunks (chunk.content, task_name, etc.).
                    See: https://docs.crewai.com/en/learn/streaming-crew-execution
            external_memory: CrewAI ExternalMemory (Redis-backed when use_crewai_external_memory=True).
                    Resolved from self.get_external_memory() in run_with_tracing when None.
        """
        # Resolve from self so run_with_tracing need not pass it (avoids CrewAI memoize serializing storage)
        if external_memory is None and self.use_crewai_external_memory:
            external_memory = self.get_external_memory()
        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,  # Set to True for debugging
            stream=stream,
            memory=False,  # Disable CrewAI default short/long/entity memory; we use external_memory only
            external_memory=external_memory,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )



### FOR TITLE GENERATION


class TitleGenerationRequest(BaseModel):
    """Request schema for title generation"""

    request_id: str = Field(..., description="Client-generated request ID")
    content: str = Field(..., description="The content to generate a title for")
    user_prompt: str | None = Field(
        None, description="Optional user prompt to modify the title"
    )
    current_title: str | None = Field(
        None, description="Current title if updating an existing one"
    )
    output_language: str = Field(
        default="en", description="Output language for the generated title (e.g., en, en-GB, fr-CA, hi-IN)"
    )


class TitlePayload(BaseModel):
    """Structured output schema for title generation"""

    title: str = Field(
        ..., description="Clear, concise title with no trailing punctuation"
    )


@CrewBase
class TitleGenerator(BaseAICrew):
    """Title generator crew: extends BaseAICrew (Custom LLM, observability, API-ready)."""
    
    agents_config = 'config/title_generator_agents.yaml'
    tasks_config = 'config/title_generator_tasks.yaml'

    def __init__(
        self,
        smtip_tid: str,
        smtip_feature: str,
        model: str,
        user_id: str,
        session_id: str,
        service_id: str,
        service_name: str,
        *,
        agent_id: str = "default",
        api: str = "completions",
        completions_endpoint: str | None = None,
        responses_endpoint: str | None = None,
        temperature: float | None = 0.7,
        max_output_tokens: int | None = None,
        reasoning_effort: str | None = None,
        instructions: str | None = None,
        trace_name: str = "crew-run",
        enable_observability: bool = True,
        use_crewai_external_memory: bool = False,
        storage_factory: Any = None,
        llm_gateway_timeout: int | None = None,
        context_window_size: int | None = None,
        retries: int | None = None,
    ):
        # Keep this BaseAICrew.__init__ as is - no changes needed
        BaseAICrew.__init__(
            self,
            smtip_tid=smtip_tid,
            smtip_feature=smtip_feature,
            model=model,
            user_id=user_id,
            session_id=session_id,
            service_id=service_id,
            service_name=service_name,
            agent_id=agent_id,
            api=api,
            completions_endpoint=completions_endpoint,
            responses_endpoint=responses_endpoint,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            reasoning_effort=reasoning_effort,
            instructions=instructions,
            trace_name=trace_name,
            enable_observability=enable_observability,
            use_crewai_external_memory=use_crewai_external_memory,
            storage_factory=storage_factory,
            llm_gateway_timeout=llm_gateway_timeout,
            context_window_size=context_window_size,
            retries=retries,
        )

    agents: List[BaseAgent]
    tasks: List[Task]
    agents_config: Dict[str, Any]
    tasks_config: Dict[str, Any]

    @agent
    def title_generator(self) -> Agent:
        return Agent(
            config=self.agents_config["title_generator"],
            verbose=True,
            llm=self.llm,
        )

    @task
    def title_generation_task(self) -> Task:
        return Task(
            config=self.tasks_config["title_generation_task"],
            output_pydantic=TitlePayload,
            # human_input = True,
        )


    @crew
    def crew(
        self,
        stream: bool = False,
        external_memory: Any = None,
    ) -> Crew:
        """Creates the TitleGenerator crew.

        Args:
            stream: If True, kickoff() returns a CrewStreamingOutput you can iterate
                    for real-time chunks (chunk.content, task_name, etc.).
                    See: https://docs.crewai.com/en/learn/streaming-crew-execution
            external_memory: CrewAI ExternalMemory (Redis-backed when use_crewai_external_memory=True).
                    Resolved from self.get_external_memory() in run_with_tracing when None.
        """
        # Resolve from self so run_with_tracing need not pass it (avoids CrewAI memoize serializing storage)
        if external_memory is None and self.use_crewai_external_memory:
            external_memory = self.get_external_memory()
        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,  # Set to True for debugging
            stream=stream,
            memory=False,  # Disable CrewAI default short/long/entity memory; we use external_memory only
            external_memory=external_memory,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )


### FOR PREVIEW GENERATION

class PreviewGenerationRequest(BaseModel):
    """Request schema for preview generation"""

    request_id: str = Field(..., description="Client-generated request ID")
    content: str = Field(
        ..., description="The newsletter content to generate a preview for"
    )
    user_prompt: str | None = Field(
        None, description="Optional user prompt to guide preview generation"
    )
    current_preview: str | None = Field(
        None, description="Current preview if updating an existing one"
    )
    output_language: str = Field(
        default="en", description="Output language for the generated preview (e.g., en, en-GB, fr-CA, hi-IN)"
    )


class PreviewPayload(BaseModel):
    """Structured output schema for preview generation"""

    preview: str = Field(
        ..., description="Engaging 15-word (+/- 5 words) summary preview"
    )

@CrewBase
class PreviewGenerator(BaseAICrew):
    """Preview generator crew: extends BaseAICrew (Custom LLM, observability, API-ready)."""
    
    agents_config = 'config/preview_generator_agents.yaml'
    tasks_config = 'config/preview_generator_tasks.yaml'

    def __init__(
        self,
        smtip_tid: str,
        smtip_feature: str,
        model: str,
        user_id: str,
        session_id: str,
        service_id: str,
        service_name: str,
        *,
        agent_id: str = "default",
        api: str = "completions",
        completions_endpoint: str | None = None,
        responses_endpoint: str | None = None,
        temperature: float | None = 0.7,
        max_output_tokens: int | None = None,
        reasoning_effort: str | None = None,
        instructions: str | None = None,
        trace_name: str = "crew-run",
        enable_observability: bool = True,
        use_crewai_external_memory: bool = False,
        storage_factory: Any = None,
        llm_gateway_timeout: int | None = None,
        context_window_size: int | None = None,
        retries: int | None = None,
    ):
        # Keep this BaseAICrew.__init__ as is - no changes needed
        BaseAICrew.__init__(
            self,
            smtip_tid=smtip_tid,
            smtip_feature=smtip_feature,
            model=model,
            user_id=user_id,
            session_id=session_id,
            service_id=service_id,
            service_name=service_name,
            agent_id=agent_id,
            api=api,
            completions_endpoint=completions_endpoint,
            responses_endpoint=responses_endpoint,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            reasoning_effort=reasoning_effort,
            instructions=instructions,
            trace_name=trace_name,
            enable_observability=enable_observability,
            use_crewai_external_memory=use_crewai_external_memory,
            storage_factory=storage_factory,
            llm_gateway_timeout=llm_gateway_timeout,
            context_window_size=context_window_size,
            retries=retries,
        )

    agents: List[BaseAgent]
    tasks: List[Task]
    agents_config: Dict[str, Any]
    tasks_config: Dict[str, Any]

    @agent
    def preview_generator(self) -> Agent:
        return Agent(
            config=self.agents_config["preview_generator"],
            verbose=True,
            llm=self.llm,
        )

    @task
    def preview_generation_task(self) -> Task:
        return Task(
            config=self.tasks_config["preview_generation_task"],
            output_pydantic=PreviewPayload,
        )


    @crew
    def crew(
        self,
        stream: bool = False,
        external_memory: Any = None,
    ) -> Crew:
        """Creates the PreviewGenerator crew.

        Args:
            stream: If True, kickoff() returns a CrewStreamingOutput you can iterate
                    for real-time chunks (chunk.content, task_name, etc.).
                    See: https://docs.crewai.com/en/learn/streaming-crew-execution
            external_memory: CrewAI ExternalMemory (Redis-backed when use_crewai_external_memory=True).
                    Resolved from self.get_external_memory() in run_with_tracing when None.
        """
        # Resolve from self so run_with_tracing need not pass it (avoids CrewAI memoize serializing storage)
        if external_memory is None and self.use_crewai_external_memory:
            external_memory = self.get_external_memory()
        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,  # Set to True for debugging
            stream=stream,
            memory=False,  # Disable CrewAI default short/long/entity memory; we use external_memory only
            external_memory=external_memory,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )


### FOR CONTENT SUMMARIZATION


class ContentSummarizationRequest(BaseModel):
    """Request schema for content summarization"""

    request_id: str = Field(..., description="Client-generated request ID")
    content: str = Field(..., description="The blog/page content to summarize")
    mode: str = Field(
        ..., description="Summarization mode: 'concise' or 'pointwise'"
    )
    company_name: str = Field(..., description="Company name for context")
    industry: str = Field(..., description="Industry for terminology alignment")
    company_description: str = Field(
        default="", description="Optional company description for additional context"
    )
    output_language: str = Field(
        default="en",
        description="Output language/locale (e.g., en, en-GB, fr-CA, hi-IN)",
    )


class ContentSummaryPayload(BaseModel):
    """Structured output schema for content summarization"""

    summary: str = Field(..., description="The generated summary text")
    mode: str = Field(..., description="The summarization mode used")
    word_count: int | None = Field(
        None, description="Word count for concise mode summaries"
    )
    point_count: int | None = Field(
        None, description="Number of bullet points for pointwise mode summaries"
    )


@CrewBase
class ContentSummariser(BaseAICrew):
    """Content summariser crew: extends BaseAICrew (Custom LLM, observability, API-ready)."""

    agents_config = "config/content_summariser_agents.yaml"
    tasks_config = "config/content_summariser_tasks.yaml"

    def __init__(
        self,
        smtip_tid: str,
        smtip_feature: str,
        model: str,
        user_id: str,
        session_id: str,
        service_id: str,
        service_name: str,
        *,
        agent_id: str = "default",
        api: str = "completions",
        completions_endpoint: str | None = None,
        responses_endpoint: str | None = None,
        temperature: float | None = 0.7,
        max_output_tokens: int | None = None,
        reasoning_effort: str | None = None,
        instructions: str | None = None,
        trace_name: str = "crew-run",
        enable_observability: bool = True,
        use_crewai_external_memory: bool = False,
        storage_factory: Any = None,
        llm_gateway_timeout: int | None = None,
        context_window_size: int | None = None,
        retries: int | None = None,
    ):
        BaseAICrew.__init__(
            self,
            smtip_tid=smtip_tid,
            smtip_feature=smtip_feature,
            model=model,
            user_id=user_id,
            session_id=session_id,
            service_id=service_id,
            service_name=service_name,
            agent_id=agent_id,
            api=api,
            completions_endpoint=completions_endpoint,
            responses_endpoint=responses_endpoint,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            reasoning_effort=reasoning_effort,
            instructions=instructions,
            trace_name=trace_name,
            enable_observability=enable_observability,
            use_crewai_external_memory=use_crewai_external_memory,
            storage_factory=storage_factory,
            llm_gateway_timeout=llm_gateway_timeout,
            context_window_size=context_window_size,
            retries=retries,
        )

    agents: List[BaseAgent]
    tasks: List[Task]
    agents_config: Dict[str, Any]
    tasks_config: Dict[str, Any]

    @agent
    def content_summariser(self) -> Agent:
        return Agent(
            config=self.agents_config["content_summariser"],
            verbose=True,
            llm=self.llm,
        )

    @task
    def content_summarisation_task(self) -> Task:
        return Task(
            config=self.tasks_config["content_summarisation_task"],
            output_pydantic=ContentSummaryPayload,
        )

    @crew
    def crew(
        self,
        stream: bool = False,
        external_memory: Any = None,
    ) -> Crew:
        """Creates the ContentSummariser crew."""
        if external_memory is None and self.use_crewai_external_memory:
            external_memory = self.get_external_memory()
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            stream=stream,
            memory=False,
            external_memory=external_memory,
        )
