"""Synlogos agent - multi-provider, multi-agent-type support"""
import asyncio
import os
import sys
from dataclasses import dataclass, field
from typing import Callable
from returns.result import Result, Success, Failure

from src.types import AgentConfig, SandboxConfig
from src.config import get_cached_config, OpenCodeConfig
from src.sandbox.local_sandbox import LocalSandbox
from src.tools.functional_tools import (
    FunctionalTool,
    create_file_read_tool,
    create_file_write_tool,
    create_file_edit_tool,
    create_shell_tool,
    create_code_tool,
    create_orchestration_tool,
)
from src.tools.advanced_tools import (
    create_glob_tool,
    create_grep_tool,
)
from src.tools.git_tools import create_all_git_tools
from src.providers.unified_provider import (
    UnifiedProviderState,
    create_unified_provider,
    run_with_prompt
)


@dataclass
class SynlogosState:
    config: AgentConfig
    agent_type: str | None
    sandbox: LocalSandbox | None = None
    provider_state: UnifiedProviderState | None = None
    messages: list[dict] = field(default_factory=list)  # Conversation history


def create_synlogos(
    config: AgentConfig | None = None,
    agent_type: str | None = None
) -> Result[SynlogosState, str]:
    """Create synlogos state with configuration"""
    cfg = config or AgentConfig()
    return Success(SynlogosState(
        config=cfg,
        agent_type=agent_type
    ))


async def start_synlogos(state: SynlogosState) -> Result[SynlogosState, str]:
    """Start the agent with proper provider initialization"""
    if state.sandbox:
        return Failure("Agent already started")
    
    # Load config from synlogos.json
    config_result = get_cached_config()
    if isinstance(config_result, Failure):
        return Failure(f"Failed to load config: {config_result.failure()}")
    
    config = config_result.unwrap()
    
    # Start sandbox
    sandbox = LocalSandbox()
    await sandbox.start()
    
    # Build internal tools (available to orchestration code)
    internal_tools: tuple[FunctionalTool, ...] = (
        create_file_read_tool(),
        create_file_write_tool(),
        create_file_edit_tool(),
        create_shell_tool(sandbox),
        create_code_tool(sandbox),
        create_glob_tool(),
        create_grep_tool(),
        *create_all_git_tools(),
    )
    
    # Only expose orchestrate tool to LLM - all other tools accessed programmatically
    tools: list[FunctionalTool] = [
        create_orchestration_tool(internal_tools, on_tool_call=lambda name, args: None)
    ]
    
    # Get agent-specific instructions from config
    custom_instructions = ""
    if state.agent_type and state.agent_type in config.agent_types:
        custom_instructions = config.agent_types[state.agent_type].instructions
    
    # Create provider based on config
    provider_result = create_unified_provider(
        config=config,
        tools=tools,
        agent_type=state.agent_type,
        model_override=state.config.model if state.config.model else None
    )
    
    if isinstance(provider_result, Failure):
        await sandbox.stop()
        return provider_result
    
    provider_state = provider_result.unwrap()
    
    return Success(SynlogosState(
        config=state.config,
        agent_type=state.agent_type,
        sandbox=sandbox,
        provider_state=provider_state
    ))


async def stop_synlogos(state: SynlogosState) -> SynlogosState:
    """Stop the agent and cleanup resources"""
    if state.sandbox:
        await state.sandbox.stop()
    return SynlogosState(
        config=state.config,
        agent_type=state.agent_type,
        sandbox=None,
        provider_state=None
    )


async def run_synlogos(
    state: SynlogosState,
    prompt: str,
    on_tool_call: Callable[[str, dict], None] | None = None,
    on_response: Callable[[str], None] | None = None,
    on_token_update: Callable[[int, int, int], None] | None = None
) -> Result[str, str]:
    """Run a prompt through the agent with conversation history"""
    if not state.provider_state:
        return Failure("Agent not started - call start() first")
    
    # Get custom instructions from config
    config_result = get_cached_config()
    custom_instructions = ""
    if isinstance(config_result, Success):
        config = config_result.unwrap()
        if state.agent_type and state.agent_type in config.agent_types:
            custom_instructions = config.agent_types[state.agent_type].instructions
    
    # Run with conversation history
    result = await run_with_prompt(
        state=state.provider_state,
        prompt=prompt,
        custom_instructions=custom_instructions,
        max_turns=state.config.max_turns,
        on_tool_call=on_tool_call,
        on_response=on_response,
        on_token_update=on_token_update,
        existing_messages=state.messages if state.messages else None
    )
    
    # Update conversation history
    if isinstance(result, Success):
        response_text, updated_messages = result.unwrap()
        state.messages.clear()
        state.messages.extend(updated_messages)
        return Success(response_text)
    else:
        return result


class Synlogos:
    """Main Synlogos agent class with async context manager support"""
    
    def __init__(
        self,
        config: AgentConfig | None = None,
        agent_type: str | None = None
    ):
        """
        Initialize Synlogos agent.
        
        Args:
            config: Agent configuration (optional, loads from synlogos.json if not provided)
            agent_type: Type of agent to use - "explore", "code", "architect", etc. (optional)
        """
        result = create_synlogos(config, agent_type)
        if isinstance(result, Failure):
            raise ValueError(f"Failed to create agent: {result.failure()}")
        self._state = result.unwrap()
    
    async def start(self) -> Result['Synlogos', str]:
        """Start the agent"""
        result = await start_synlogos(self._state)
        if isinstance(result, Success):
            state = result.unwrap()
            self._state = state
            return Success(self)
        return Failure(result.failure())
    
    async def stop(self) -> Result[None, str]:
        """Stop the agent"""
        self._state = await stop_synlogos(self._state)
        return Success(None)
    
    async def run(
        self,
        prompt: str,
        on_tool_call: Callable[[str, dict], None] | None = None,
        on_response: Callable[[str], None] | None = None,
        on_token_update: Callable[[int, int, int], None] | None = None
    ) -> Result[str, str]:
        """
        Run a prompt through the agent.
        
        Args:
            prompt: The user prompt
            on_tool_call: Callback for tool calls
            on_response: Callback for LLM responses
            on_token_update: Callback for token usage updates (prompt, completion, total)
        
        Returns:
            Result with the final response or error
        """
        return await run_synlogos(self._state, prompt, on_tool_call, on_response, on_token_update)
    
    @property
    def provider_name(self) -> str | None:
        """Get current provider name"""
        if self._state.provider_state:
            return self._state.provider_state.provider_name
        return None
    
    @property
    def model_name(self) -> str | None:
        """Get current model name"""
        if self._state.provider_state:
            return self._state.provider_state.model
        return None
    
    @property
    def token_usage(self):
        """Get token usage stats"""
        if self._state.provider_state:
            return self._state.provider_state.token_usage
        return None
    
    async def __aenter__(self):
        """Async context manager entry"""
        result = await self.start()
        if isinstance(result, Failure):
            raise RuntimeError(f"Failed to start agent: {result.failure()}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()
        return False  # Don't suppress exceptions


def list_agent_types() -> list[str]:
    """List available agent types from config"""
    result = get_cached_config()
    if isinstance(result, Success):
        return list(result.unwrap().agent_types.keys())
    return []


def get_agent_info(agent_type: str) -> dict | None:
    """Get information about a specific agent type"""
    result = get_cached_config()
    if isinstance(result, Success):
        config = result.unwrap()
        if agent_type in config.agent_types:
            agent_config = config.agent_types[agent_type]
            return {
                "type": agent_type,
                "provider": agent_config.provider,
                "model": agent_config.model,
                "has_custom_instructions": bool(agent_config.instructions)
            }
    return None
