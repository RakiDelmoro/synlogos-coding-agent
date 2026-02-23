import asyncio
import os
import sys
from dataclasses import dataclass
from typing import Callable
from returns.result import Result, Success, Failure

from src.types import AgentConfig, SandboxConfig
from src.sandbox.local_sandbox import LocalSandbox
from src.tools.functional_tools import (
    FunctionalTool,
    create_file_read_tool,
    create_file_write_tool,
    create_file_edit_tool,
    create_shell_tool,
    create_code_tool,
)
from src.tools.advanced_tools import (
    create_glob_tool,
    create_grep_tool,
)
from src.tools.git_tools import create_all_git_tools
from src.providers.functional_provider import ProviderState, create_provider, run_with_prompt


@dataclass(frozen=True)
class SynlogosState:
    config: AgentConfig
    api_key: str
    sandbox: LocalSandbox | None = None
    provider_state: ProviderState | None = None


def create_synlogos(
    config: AgentConfig | None = None,
    api_key: str | None = None
) -> SynlogosState:
    return SynlogosState(
        config=config or AgentConfig(),
        api_key=api_key or os.environ.get("TOGETHER_API_KEY", "")
    )


async def start_synlogos(state: SynlogosState) -> Result[SynlogosState, str]:
    if state.sandbox:
        return Failure("Agent already started")
    
    sandbox = LocalSandbox()
    await sandbox.start()
    
    tools: list[FunctionalTool] = [
        create_file_read_tool(),
        create_file_write_tool(),
        create_file_edit_tool(),
        create_shell_tool(sandbox),
        create_code_tool(sandbox),
        create_glob_tool(),
        create_grep_tool(),
        *create_all_git_tools(),
    ]
    
    provider_state = create_provider(
        api_key=state.api_key,
        tools=tools,
        model=state.config.model
    )
    
    return Success(SynlogosState(
        config=state.config,
        api_key=state.api_key,
        sandbox=sandbox,
        provider_state=provider_state
    ))


async def stop_synlogos(state: SynlogosState) -> SynlogosState:
    if state.sandbox:
        await state.sandbox.stop()
    return SynlogosState(
        config=state.config,
        api_key=state.api_key,
        sandbox=None,
        provider_state=None
    )


async def run_synlogos(
    state: SynlogosState,
    prompt: str,
    on_tool_call: Callable[[str, dict], None] | None = None,
    on_response: Callable[[str], None] | None = None
) -> Result[str, str]:
    if not state.provider_state:
        return Failure("Agent not started")
    return await run_with_prompt(
        state=state.provider_state,
        prompt=prompt,
        instructions=state.config.instructions,
        max_turns=state.config.max_turns,
        on_tool_call=on_tool_call,
        on_response=on_response
    )


class Synlogos:
    def __init__(self, config: AgentConfig | None = None, api_key: str | None = None):
        self._state = create_synlogos(config, api_key)
    
    async def start(self) -> Result[None, str]:
        result = await start_synlogos(self._state)
        if isinstance(result, Success):
            self._state = result.unwrap()
            return Success(None)
        return result
    
    async def stop(self) -> Result[None, str]:
        self._state = await stop_synlogos(self._state)
        return Success(None)
    
    async def run(
        self,
        prompt: str,
        on_tool_call: Callable[[str, dict], None] | None = None,
        on_response: Callable[[str], None] | None = None
    ) -> Result[str, str]:
        return await run_synlogos(self._state, prompt, on_tool_call, on_response)
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, *args):
        await self.stop()
