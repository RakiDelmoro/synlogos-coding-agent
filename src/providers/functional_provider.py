import os
import json
from typing import Callable, Any
from dataclasses import dataclass, field
from together import Together
from returns.result import Result, Success, Failure

from src.types import ToolResult
from src.tools.functional_tools import FunctionalTool


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def add(self, prompt: int, completion: int):
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion


@dataclass
class ProviderState:
    client: Together
    model: str
    tools: tuple[FunctionalTool, ...]
    tool_map: dict[str, FunctionalTool]
    token_usage: TokenUsage = field(default_factory=TokenUsage)


def get_system_prompt() -> str:
    cwd = os.getcwd()
    return f"""You are an AI coding agent with access to tools for file operations, shell commands, and code execution.

Working directory: {cwd}

You have these tools:
- write_file: Save code/content to a file (persists on disk)
- read_file: Read a file from disk
- edit_file: Edit an existing file
- execute_code: Run Python/JavaScript code (does NOT save to disk)
- shell: Run shell commands

IMPORTANT RULES:
1. When asked to "create a file", "write a module", "save code" - ALWAYS use write_file, NOT execute_code
2. Use execute_code only for quick tests or when user specifically asks to "run this code"
3. Always save files to {cwd} (the working directory)
4. After writing files, you can use shell or execute_code to test them

When a user asks you to do something:
1. Plan your approach before acting
2. Create files with write_file when building modules/scripts
3. Test your work by running the files
4. Report results clearly

Always think through problems step by step. If something fails, debug and try again."""


def create_provider(api_key: str, tools: list[FunctionalTool], model: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo") -> ProviderState:
    client = Together(api_key=api_key)
    tool_map = {t.name: t for t in tools}
    return ProviderState(
        client=client,
        model=model,
        tools=tuple(tools),
        tool_map=tool_map
    )


def build_system_prompt(instructions: str | None = None) -> str:
    base = get_system_prompt()
    if instructions:
        return f"{base}\n\n{instructions}"
    return base


def build_tool_definitions(tools: tuple[FunctionalTool, ...]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters_schema
            }
        }
        for t in tools
    ]


def build_messages(prompt: str, instructions: str | None = None) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": build_system_prompt(instructions)},
        {"role": "user", "content": prompt}
    ]


async def execute_tool(
    state: ProviderState,
    tool_name: str,
    arguments: dict
) -> Result[ToolResult, str]:
    tool = state.tool_map.get(tool_name)
    if not tool:
        return Failure(f"Unknown tool: {tool_name}")
    return await tool.execute(**arguments)


async def process_tool_call(
    state: ProviderState,
    tool_call: Any,
    on_tool_call: Callable[[str, dict], None] | None = None
) -> dict[str, Any]:
    tool_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)
    
    if on_tool_call:
        on_tool_call(tool_name, arguments)
    
    result = await execute_tool(state, tool_name, arguments)
    
    if isinstance(result, Success):
        content = result.unwrap().model_dump_json()
    else:
        content = json.dumps({"error": result.failure()})
    
    return {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": content
    }


async def run_completion(
    state: ProviderState,
    messages: list[dict[str, Any]],
    tool_defs: list[dict[str, Any]] | None
) -> Result[tuple[dict[str, Any], list[dict[str, Any]]], str]:
    try:
        response = state.client.chat.completions.create(
            model=state.model,
            messages=messages,
            tools=tool_defs,
            tool_choice="auto" if tool_defs else None,
        )
        
        if response.usage:
            state.token_usage.add(
                response.usage.prompt_tokens,
                response.usage.completion_tokens
            )
        
        assistant_message = response.choices[0].message
        return Success((assistant_message.model_dump(), messages))
    except Exception as e:
        return Failure(str(e))


async def run_agent_loop(
    state: ProviderState,
    messages: list[dict[str, Any]],
    max_turns: int,
    on_tool_call: Callable[[str, dict], None] | None = None,
    on_response: Callable[[str], None] | None = None
) -> Result[str, str]:
    tool_defs = build_tool_definitions(state.tools) if state.tools else None
    
    for _ in range(max_turns):
        result = await run_completion(state, messages, tool_defs)
        
        if isinstance(result, Failure):
            return result
        
        assistant_msg, messages = result.unwrap()
        messages.append(assistant_msg)
        
        content = assistant_msg.get("content")
        tool_calls = assistant_msg.get("tool_calls")
        
        if content and on_response:
            on_response(content)
        
        if not tool_calls:
            return Success(content or "")
        
        for tool_call_data in tool_calls:
            class ToolCallWrapper:
                def __init__(self, data: dict):
                    self.id = data["id"]
                    self.function = type('obj', (object,), {
                        'name': data["function"]["name"],
                        'arguments': data["function"]["arguments"]
                    })()
            
            tool_call = ToolCallWrapper(tool_call_data)
            tool_response = await process_tool_call(state, tool_call, on_tool_call)
            messages.append(tool_response)
    
    return Success("Max turns reached without completion.")


async def run_with_prompt(
    state: ProviderState,
    prompt: str,
    instructions: str | None = None,
    max_turns: int = 20,
    on_tool_call: Callable[[str, dict], None] | None = None,
    on_response: Callable[[str], None] | None = None
) -> Result[str, str]:
    messages = build_messages(prompt, instructions)
    return await run_agent_loop(state, messages, max_turns, on_tool_call, on_response)
