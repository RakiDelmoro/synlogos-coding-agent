import os
import json
from typing import Callable, Any
from dataclasses import dataclass, field
from anthropic import Anthropic
from returns.result import Result, Success, Failure

from src.types import ToolResult
from src.tools.functional_tools import FunctionalTool


@dataclass
class AnthropicTokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    
    def add(self, input_t: int, output_t: int):
        self.input_tokens += input_t
        self.output_tokens += output_t
        self.total_tokens += input_t + output_t


@dataclass
class AnthropicProviderState:
    client: Anthropic
    model: str
    tools: tuple[FunctionalTool, ...]
    tool_map: dict[str, FunctionalTool]
    token_usage: AnthropicTokenUsage = field(default_factory=AnthropicTokenUsage)


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


def create_anthropic_provider(
    api_key: str,
    tools: list[FunctionalTool],
    model: str = "claude-3-sonnet-20240229"
) -> AnthropicProviderState:
    client = Anthropic(api_key=api_key)
    tool_map = {t.name: t for t in tools}
    return AnthropicProviderState(
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


def build_anthropic_tool_definitions(tools: tuple[FunctionalTool, ...]) -> list[dict[str, Any]]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.parameters_schema
        }
        for t in tools
    ]


def build_anthropic_messages(prompt: str, instructions: str | None = None) -> list[dict[str, Any]]:
    return [
        {"role": "user", "content": prompt}
    ]


def extract_tool_calls(content_blocks: list) -> list[dict]:
    """Extract tool_use blocks from Anthropic response content."""
    tool_calls = []
    for block in content_blocks:
        if block.type == "tool_use":
            tool_calls.append({
                "id": block.id,
                "name": block.name,
                "input": block.input
            })
    return tool_calls


def extract_text_content(content_blocks: list) -> str:
    """Extract text content from Anthropic response."""
    texts = []
    for block in content_blocks:
        if block.type == "text":
            texts.append(block.text)
    return "\n".join(texts)


async def execute_anthropic_tool(
    state: AnthropicProviderState,
    tool_name: str,
    arguments: dict
) -> Result[ToolResult, str]:
    tool = state.tool_map.get(tool_name)
    if not tool:
        return Failure(f"Unknown tool: {tool_name}")
    return await tool.execute(**arguments)


async def process_anthropic_tool_call(
    state: AnthropicProviderState,
    tool_call: dict,
    on_tool_call: Callable[[str, dict], None] | None = None
) -> dict[str, Any]:
    tool_name = tool_call["name"]
    tool_id = tool_call["id"]
    arguments = tool_call["input"]
    
    if on_tool_call:
        on_tool_call(tool_name, arguments)
    
    result = await execute_anthropic_tool(state, tool_name, arguments)
    
    if isinstance(result, Success):
        content = result.unwrap().model_dump_json()
    else:
        content = json.dumps({"error": result.failure()})
    
    return {
        "type": "tool_result",
        "tool_use_id": tool_id,
        "content": content
    }


async def run_anthropic_completion(
    state: AnthropicProviderState,
    messages: list[dict[str, Any]],
    tool_defs: list[dict[str, Any]] | None,
    system: str
) -> Result[tuple[list, list[dict[str, Any]]], str]:
    try:
        response = state.client.messages.create(
            model=state.model,
            max_tokens=4096,
            system=system,
            messages=messages,
            tools=tool_defs if tool_defs else None,
        )
        
        if response.usage:
            state.token_usage.add(
                response.usage.input_tokens,
                response.usage.output_tokens
            )
        
        return Success((response.content, messages))
    except Exception as e:
        return Failure(str(e))


async def run_anthropic_agent_loop(
    state: AnthropicProviderState,
    messages: list[dict[str, Any]],
    max_turns: int,
    system: str,
    on_tool_call: Callable[[str, dict], None] | None = None,
    on_response: Callable[[str], None] | None = None
) -> Result[str, str]:
    tool_defs = build_anthropic_tool_definitions(state.tools) if state.tools else None
    
    for turn in range(max_turns):
        result = await run_anthropic_completion(state, messages, tool_defs, system)
        
        if isinstance(result, Failure):
            return result
        
        content_blocks, _ = result.unwrap()
        
        text_content = extract_text_content(content_blocks)
        tool_calls = extract_tool_calls(content_blocks)
        
        if text_content and on_response:
            on_response(text_content)
        
        if not tool_calls:
            return Success(text_content or "")
        
        # Build message with assistant's response
        assistant_content = []
        for block in content_blocks:
            if block.type == "text":
                assistant_content.append({
                    "type": "text",
                    "text": block.text
                })
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })
        
        messages.append({
            "role": "assistant",
            "content": assistant_content
        })
        
        # Process tool calls and add results
        tool_results = []
        for tool_call in tool_calls:
            tool_result = await process_anthropic_tool_call(state, tool_call, on_tool_call)
            tool_results.append(tool_result)
        
        messages.append({
            "role": "user",
            "content": tool_results
        })
    
    return Success("Max turns reached without completion.")


async def run_with_anthropic_prompt(
    state: AnthropicProviderState,
    prompt: str,
    instructions: str | None = None,
    max_turns: int = 20,
    on_tool_call: Callable[[str, dict], None] | None = None,
    on_response: Callable[[str], None] | None = None
) -> Result[str, str]:
    system = build_system_prompt(instructions)
    messages = build_anthropic_messages(prompt, instructions)
    return await run_anthropic_agent_loop(state, messages, max_turns, system, on_tool_call, on_response)
