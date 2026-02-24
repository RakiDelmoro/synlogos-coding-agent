"""Unified provider manager that routes to the correct provider based on config"""

import os
from typing import Callable, Any
from dataclasses import dataclass, field
from openai import OpenAI
from returns.result import Result, Success, Failure

from src.types import ToolResult
from src.tools.functional_tools import FunctionalTool
from src.config import OpenCodeConfig, get_agent_config


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    # Cost tracking
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    total_cost: float = 0.0

    def add(self, prompt: int, completion: int):
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion
        # Calculate cost
        input_cost = (prompt / 1000) * self.input_cost_per_1k
        output_cost = (completion / 1000) * self.output_cost_per_1k
        self.total_cost += input_cost + output_cost

    @property
    def cost_str(self) -> str:
        """Return formatted cost string like OpenCode: $4.68"""
        if self.total_cost == 0:
            return "$0.00"
        return f"${self.total_cost:.2f}"


@dataclass
class UnifiedProviderState:
    """State for the unified provider - wraps OpenAI client"""

    client: OpenAI
    provider_name: str
    model: str
    tools: tuple[FunctionalTool, ...]
    tool_map: dict[str, FunctionalTool]
    base_url: str
    api_key: str | None
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    config: OpenCodeConfig | None = None  # Store config for access to raw_instructions


# System prompt (same for all providers) - Ultra minimal for low token usage
SYSTEM_PROMPT_TEMPLATE = """cwd:{cwd}|tools:read,write,edit,shell,exec,glob,grep,git,orchestrate|rule:simple=direct,multi=orchestrate,ask=answer|err=explain"""


def create_unified_provider(
    config: OpenCodeConfig,
    tools: list[FunctionalTool],
    agent_type: str | None = None,
    model_override: str | None = None,
) -> Result[UnifiedProviderState, str]:
    """Create a unified provider based on configuration"""

    # Get agent configuration
    agent_config_result = get_agent_config(config, agent_type, model_override)
    if isinstance(agent_config_result, Failure):
        return agent_config_result

    provider_name, model, api_key, agent_instructions = agent_config_result.unwrap()

    # Get provider config for base URL
    if provider_name not in config.providers:
        return Failure(f"Unknown provider: {provider_name}")

    provider_config = config.providers[provider_name]
    base_url = provider_config.base_url

    # Create OpenAI client (all providers use OpenAI-compatible API)
    try:
        client = OpenAI(
            base_url=base_url,
            api_key=api_key or "not-needed",  # Some local providers don't require API keys
        )
    except Exception as e:
        return Failure(f"Failed to create client: {e}")

    tool_map = {t.name: t for t in tools}

    return Success(
        UnifiedProviderState(
            client=client,
            provider_name=provider_name,
            model=model,
            tools=tuple(tools),
            tool_map=tool_map,
            base_url=base_url,
            api_key=api_key,
            config=config,  # Store config for access to raw_instructions
        )
    )


def build_system_prompt(custom_instructions: str = "", raw_instructions: str = "") -> str:
    """Build system prompt with optional custom instructions and skills"""
    cwd = os.getcwd()
    base_prompt = SYSTEM_PROMPT_TEMPLATE.format(cwd=cwd, custom_instructions=custom_instructions)

    # Add skills.md content if available
    if raw_instructions:
        base_prompt = f"{base_prompt}\n\n## Your Skills\n{raw_instructions}"

    return base_prompt


def build_messages(
    prompt: str, custom_instructions: str = "", raw_instructions: str = ""
) -> list[dict[str, Any]]:
    """Build message list with system prompt and user prompt"""
    return [
        {"role": "system", "content": build_system_prompt(custom_instructions, raw_instructions)},
        {"role": "user", "content": prompt},
    ]


def build_tool_definitions(tools: tuple[Any, ...]) -> list[dict[str, Any]]:
    """Build tool definitions for API"""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters_schema,
            },
        }
        for t in tools
    ]


async def execute_tool(
    state: UnifiedProviderState, tool_name: str, arguments: dict
) -> Result[ToolResult, str]:
    """Execute a tool by name"""
    tool = state.tool_map.get(tool_name)
    if not tool:
        return Failure(f"Unknown tool: {tool_name}")
    return await tool.execute(**arguments)


import json
import re


def clean_tool_arguments(arguments_str: str) -> dict:
    """Clean and parse tool arguments, handling malformed JSON from LLM"""
    # First, replace actual control characters that appear in strings
    # This handles the case where LLM puts actual newlines in JSON strings
    cleaned = arguments_str

    # Replace actual newlines and carriage returns with escaped versions
    # We need to be careful not to double-escape already-escaped ones
    # Use a placeholder approach
    cleaned = cleaned.replace("\\\\n", "\x00ESCAPED_N\x00")
    cleaned = cleaned.replace("\\\\r", "\x00ESCAPED_R\x00")
    cleaned = cleaned.replace("\n", "\\n")
    cleaned = cleaned.replace("\r", "\\r")
    cleaned = cleaned.replace("\x00ESCAPED_N\x00", "\\\\n")
    cleaned = cleaned.replace("\x00ESCAPED_R\x00", "\\\\r")

    # Now try to parse the JSON
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        # If still failing, try more aggressive cleaning
        # Handle unescaped quotes within strings
        # This is a last resort - try to fix common quote issues
        try:
            # Replace problematic control characters
            cleaned2 = re.sub(r"[\x00-\x1f]", "", cleaned)  # Remove control chars
            return json.loads(cleaned2)
        except json.JSONDecodeError:
            return {"error": f"Failed to parse tool arguments: {e}", "raw": arguments_str[:200]}


async def process_tool_call(
    state: UnifiedProviderState,
    tool_call: Any,
    on_tool_call: Callable[[str, dict], None] | None = None,
    on_tool_result: Callable[[str, dict, str], None] | None = None,
) -> dict[str, Any]:
    """Process a single tool call"""
    tool_name = tool_call.function.name
    arguments = clean_tool_arguments(tool_call.function.arguments)

    if on_tool_call:
        on_tool_call(tool_name, arguments)

    result = await execute_tool(state, tool_name, arguments)

    if isinstance(result, Success):
        content = result.unwrap().model_dump_json()
        if on_tool_result:
            on_tool_result(tool_name, arguments, result.unwrap().output)
    else:
        content = json.dumps({"error": result.failure()})
        if on_tool_result:
            on_tool_result(tool_name, arguments, f"Error: {result.failure()}")

    return {"role": "tool", "tool_call_id": tool_call.id, "content": content}


async def run_completion(
    state: UnifiedProviderState,
    messages: list[dict[str, Any]],
    tool_defs: list[dict[str, Any]] | None,
    on_token_update: Callable[[int, int, int], None] | None = None,
) -> Result[tuple[dict[str, Any], list[dict[str, Any]]], str]:
    """Run a completion with the provider"""
    try:
        response = state.client.chat.completions.create(
            model=state.model,
            messages=messages,
            tools=tool_defs,
            tool_choice="auto" if tool_defs else None,
        )

        # Track token usage if available
        if hasattr(response, "usage") and response.usage:
            prompt_tokens = getattr(response.usage, "prompt_tokens", 0)
            completion_tokens = getattr(response.usage, "completion_tokens", 0)
            state.token_usage.add(prompt_tokens, completion_tokens)

            # Notify callback if provided
            if on_token_update:
                on_token_update(
                    state.token_usage.prompt_tokens,
                    state.token_usage.completion_tokens,
                    state.token_usage.total_tokens,
                )

        assistant_message = response.choices[0].message
        return Success((assistant_message.model_dump(), messages))
    except Exception as e:
        return Failure(f"{state.provider_name} API error: {e}")


async def run_agent_loop(
    state: UnifiedProviderState,
    messages: list[dict[str, Any]],
    max_turns: int,
    on_tool_call: Callable[[str, dict], None] | None = None,
    on_response: Callable[[str], None] | None = None,
    on_token_update: Callable[[int, int, int], None] | None = None,
    on_tool_result: Callable[[str, dict, str], None] | None = None,
) -> Result[str, str]:
    """Run the agent loop with tool calling"""
    tool_defs = build_tool_definitions(state.tools) if state.tools else None
    orchestrate_called = False

    for turn in range(max_turns):
        result = await run_completion(state, messages, tool_defs, on_token_update)

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

        # Process tool calls
        for tool_call_data in tool_calls:

            class ToolCallWrapper:
                def __init__(self, data: dict):
                    self.id = data["id"]
                    self.function = type(
                        "obj",
                        (object,),
                        {
                            "name": data["function"]["name"],
                            "arguments": data["function"]["arguments"],
                        },
                    )()

            tool_call = ToolCallWrapper(tool_call_data)
            tool_name = tool_call_data["function"]["name"]

            # Check if trying to call orchestrate again
            if tool_name == "orchestrate" and orchestrate_called:
                # Force stop after multiple orchestrate calls - task should be done
                return Success("Task completed via orchestrate.")

            if tool_name == "orchestrate":
                orchestrate_called = True

            tool_response = await process_tool_call(state, tool_call, on_tool_call, on_tool_result)
            messages.append(tool_response)

        # After first orchestrate, remind the LLM to stop calling tools and INCLUDE RESULTS
        if orchestrate_called and turn == 0:
            messages.append(
                {
                    "role": "system",
                    "content": "STOP. The orchestrate tool has been executed. DO NOT call any more tools. CRITICAL: Your next response MUST include the actual results/content discovered by the tools - NEVER just say 'Task completed' or 'Done'. Check the tool output messages for actual results. If there was an error, explain what went wrong. If there was output, describe what was found. Analyze the tool results and provide a complete answer to the user's question.",
                }
            )

    return Success("Max turns reached without completion.")


async def run_with_prompt(
    state: UnifiedProviderState,
    prompt: str,
    custom_instructions: str = "",
    max_turns: int = 20,
    on_tool_call: Callable[[str, dict], None] | None = None,
    on_response: Callable[[str], None] | None = None,
    on_token_update: Callable[[int, int, int], None] | None = None,
    existing_messages: list[dict[str, Any]] | None = None,
    on_tool_result: Callable[[str, dict, str], None] | None = None,
) -> Result[tuple[str, list[dict[str, Any]]], str]:
    """Main entry point for running with a prompt

    Returns:
        Success with (response_text, updated_messages) to maintain conversation history
    """
    # Get raw_instructions from config if available
    raw_instructions = ""
    if state.config:
        raw_instructions = state.config.raw_instructions

    if existing_messages:
        # Continue existing conversation
        messages = existing_messages.copy()
        messages.append({"role": "user", "content": prompt})
    else:
        # Start fresh conversation with skills from config
        messages = build_messages(prompt, custom_instructions, raw_instructions)

    result = await run_agent_loop(
        state, messages, max_turns, on_tool_call, on_response, on_token_update, on_tool_result
    )

    if isinstance(result, Success):
        # Return both the response text and the updated messages for history
        return Success((result.unwrap(), messages))
    else:
        return Failure(result.failure())
