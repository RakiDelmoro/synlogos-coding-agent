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
    
    def add(self, prompt: int, completion: int):
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion


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


# System prompt (same for all providers)
SYSTEM_PROMPT_TEMPLATE = """You are an AI coding agent that uses programmatic tool calling for all tasks.

Working directory: {cwd}

{custom_instructions}

THINKING VISIBILITY - SHOW YOUR REASONING:
Before using any tools, ALWAYS explain your thinking process. This helps users understand your approach.

For complex tasks, structure your response as:
1. **Understanding**: What does the user want?
2. **Approach**: How will you accomplish this?
3. **Execution**: Call the appropriate tool

Example:
User: "Find all Python files and check for syntax errors"

Your response:
"I'll help you find Python files and check for syntax errors. Let me break this down:
- First, I'll search for all .py files in the workspace
- Then I'll use Python's compileall module to check syntax
- Finally, I'll report any errors found"
[Then call orchestrate with the code]

PRIMARY WORKFLOW:
You have ONE tool: `orchestrate`. Use it when the user asks you to DO something (write files, edit code, search, run commands, etc.).

WHEN TO USE ORCHESTRATE:
- User asks to "write/create/save a file" → use orchestrate with write_file()
- User asks to "edit/modify/update code" → use orchestrate with edit_file()
- User asks to "search/find/read files" → use orchestrate with grep/glob/read_file
- User asks to "run/execute/test code" → use orchestrate with shell() or execute_code()
- Complex multi-step tasks → use orchestrate to batch operations

WHEN NOT TO USE ORCHESTRATE:
- Simple questions ("What is 2+2?", "Is 11 prime?") → Just answer directly, NO tool call
- Explanations or advice → Just answer directly, NO tool call
- Already completed the task → Just answer directly, NO tool call

HOW ORCHESTRATE WORKS:
- You write Python code that runs INSIDE an async environment
- Use `await` directly (NO need for asyncio.run() or async def main())
- Call tools like: `result = await read_file("path")`
- Return results via print() or by setting a `result` variable
- The code runs immediately when you call orchestrate

CODE FORMATTING FOR JSON - CRITICAL:
The orchestrate tool expects valid JSON with the code as a STRING VALUE. When writing multi-line code:
- The CODE PARAMETER IS A STRING - all code must be on one line with \n for newlines
- Example: code="await write_file('/workspaces/synlogos/hello.txt','Hello')"
- For multi-line strings: content = "line1\nline2\nline3"  
- WRONG: code="line1
line2"  (actual newline breaks JSON)
- CORRECT: code="line1\nline2"  (escaped newline in string)
- NEVER use triple quotes in the code parameter

TOOL AVAILABILITY (accessible via orchestrate code):
- await read_file(path, offset=1, limit=2000): Read files
- await write_file(path, content): Write/create files  
- await edit_file(path, old_string, new_string, replace_all=False): Edit files
- await shell(command, timeout=120, workdir=None): Run shell commands
- await execute_code(code, language="python", timeout=30): Execute code
- await glob(pattern, path=None): Search files by pattern
- await grep(pattern, path, include=None): Search file contents
- await git_status(), git_diff(), git_log(), git_commit(message): Git operations

IMPORTANT RULES:
1. DO NOT use import asyncio or asyncio.run() - the code already runs async
2. DO NOT define async def main() - just write code that uses await directly
3. Use await when calling tools
4. Check result.error before using result.output
5. Return results via print() or result variable
6. WHEN USER SAYS "write/create/save a file" → use write_file() to save to disk
7. WHEN USER SAYS "run/test/execute code" → use execute_code() for temporary execution
8. NEVER use execute_code when user asks to "create a file" or "write a module"

CRITICAL - ALWAYS PRINT OR CAPTURE RESULTS:
When you call a tool, you MUST either:
- Print the result: `print((await write_file("path", "content")).output)`
- Or assign and print: `result = await write_file("path", "content")` then `print(result.output)`
- Or return via result variable: `result = await write_file("path", "content")`

EXACT TEMPLATE for writing a file:

FOR RUST CODE (multi-line):
  content = 'fn main() {{ NEWLINE    println!("Hello, world!"); NEWLINE}} NEWLINE'
  result = await write_file("/workspaces/synlogos/hello.rs", content)
  if result.error:
      print("FAILED: " + result.error)
  else:
      print("SUCCESS: " + result.output)

FOR SIMPLE TEXT (single-line):
  content = "Hello, world!"
  result = await write_file("/workspaces/synlogos/test.txt", content)
  print(result.output if not result.error else result.error)

CRITICAL: Replace NEWLINE with backslash-n in your code. Use single quotes for content strings.
NEVER claim success unless output shows "SUCCESS" or "Successfully wrote"!

Example for reading a file:
```python
result = await read_file("/workspaces/synlogos/test.txt")
if result.error:
    print("Error: " + result.error)
else:
    print(result.output)
```

WORKFLOW:
1. Analyze the request - is it a task to DO or a question to ANSWER?
2. If it's a TASK (write/edit/run/search): Call orchestrate(code="...") with code that completes it
3. If it's a QUESTION (what/how/why): Just answer directly with NO tool call
4. After orchestrate completes, RESPOND WITH THE ACTUAL RESULTS - not just confirmation

CRITICAL - RESPOND WITH ACTUAL RESULTS, NOT CONFIRMATIONS:
When tools complete, you MUST provide the actual answer/data/results in your response:

✅ GOOD (summarizes actual findings):
"This project is Synlogos - a multi-provider AI coding agent with JSON configuration. It supports multiple LLM providers (opencode.ai, ollama, togetherai) and specialized agent types (explore, code, architect, etc.). The codebase is built with Python using functional programming patterns."

❌ BAD (just confirms tools ran):
"Task completed via orchestrate."
"The search has been performed."
"Files have been found."

CRITICAL RULES:
1. After tool execution, ALWAYS read the results and include them in your response
2. NEVER say "Task completed" or "Done" without the actual content
3. If you searched → describe what you found
4. If you read files → summarize the content
5. If you explored → explain what you discovered
6. Your FINAL RESPONSE is what the user sees - make it useful!

Always think through problems step by step."""


def create_unified_provider(
    config: OpenCodeConfig,
    tools: list[FunctionalTool],
    agent_type: str | None = None,
    model_override: str | None = None
) -> Result[UnifiedProviderState, str]:
    """Create a unified provider based on configuration"""
    
    # Get agent configuration
    agent_config_result = get_agent_config(config, agent_type, model_override)
    if isinstance(agent_config_result, Failure):
        return agent_config_result
    
    provider_name, model, api_key, instructions = agent_config_result.unwrap()
    
    # Get provider config for base URL
    if provider_name not in config.providers:
        return Failure(f"Unknown provider: {provider_name}")
    
    provider_config = config.providers[provider_name]
    base_url = provider_config.base_url
    
    # Create OpenAI client (all providers use OpenAI-compatible API)
    try:
        client = OpenAI(
            base_url=base_url,
            api_key=api_key or "not-needed"  # Some local providers don't require API keys
        )
    except Exception as e:
        return Failure(f"Failed to create client: {e}")
    
    tool_map = {t.name: t for t in tools}
    
    return Success(UnifiedProviderState(
        client=client,
        provider_name=provider_name,
        model=model,
        tools=tuple(tools),
        tool_map=tool_map,
        base_url=base_url,
        api_key=api_key
    ))


def build_system_prompt(custom_instructions: str = "") -> str:
    """Build system prompt with optional custom instructions"""
    cwd = os.getcwd()
    return SYSTEM_PROMPT_TEMPLATE.format(cwd=cwd, custom_instructions=custom_instructions)


def build_tool_definitions(tools: tuple[FunctionalTool, ...]) -> list[dict[str, Any]]:
    """Build tool definitions for OpenAI API"""
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


def build_messages(prompt: str, custom_instructions: str = "") -> list[dict[str, Any]]:
    """Build message list for API"""
    return [
        {"role": "system", "content": build_system_prompt(custom_instructions)},
        {"role": "user", "content": prompt}
    ]


async def execute_tool(
    state: UnifiedProviderState,
    tool_name: str,
    arguments: dict
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
    try:
        # Try standard JSON parsing first
        return json.loads(arguments_str)
    except json.JSONDecodeError:
        # If that fails, try to fix common issues
        cleaned = arguments_str
        
        # Handle the specific case where LLM put actual newlines in a JSON string
        # This happens with orchestrate code parameter
        if '"code":' in cleaned or "'code':" in cleaned:
            # Extract the code value between quotes
            patterns = [
                r'"code":\s*"(.*?)"(?=,|})',
                r"'code':\s*'(.*?)'(?=,|})",
                r'"code":\s*"(.*)"$',
                r"'code':\s*'(.*)'$"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, cleaned, re.DOTALL)
                if match:
                    code_content = match.group(1)
                    # Replace actual newlines with escaped newlines in the content
                    code_content_fixed = code_content.replace('\n', '\\n').replace('\r', '\\r')
                    # Replace quotes inside the content
                    code_content_fixed = code_content_fixed.replace('"', '\\"')
                    # Reconstruct the JSON
                    cleaned = cleaned[:match.start(1)] + code_content_fixed + cleaned[match.end(1):]
                    break
        
        # General newline cleanup for other parameters
        cleaned = cleaned.replace('\n', '\\n').replace('\r', '\\r')
        
        # Try parsing again
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            # If still failing, return error in result format
            return {"error": f"Failed to parse tool arguments: {e}", "raw": arguments_str[:200]}


async def process_tool_call(
    state: UnifiedProviderState,
    tool_call: Any,
    on_tool_call: Callable[[str, dict], None] | None = None
) -> dict[str, Any]:
    """Process a single tool call"""
    tool_name = tool_call.function.name
    arguments = clean_tool_arguments(tool_call.function.arguments)
    
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
    state: UnifiedProviderState,
    messages: list[dict[str, Any]],
    tool_defs: list[dict[str, Any]] | None,
    on_token_update: Callable[[int, int, int], None] | None = None
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
        if hasattr(response, 'usage') and response.usage:
            prompt_tokens = getattr(response.usage, 'prompt_tokens', 0)
            completion_tokens = getattr(response.usage, 'completion_tokens', 0)
            state.token_usage.add(prompt_tokens, completion_tokens)
            
            # Notify callback if provided
            if on_token_update:
                on_token_update(
                    state.token_usage.prompt_tokens,
                    state.token_usage.completion_tokens,
                    state.token_usage.total_tokens
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
    on_token_update: Callable[[int, int, int], None] | None = None
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
                    self.function = type('obj', (object,), {
                        'name': data["function"]["name"],
                        'arguments': data["function"]["arguments"]
                    })()
            
            tool_call = ToolCallWrapper(tool_call_data)
            tool_name = tool_call_data["function"]["name"]
            
            # Check if trying to call orchestrate again
            if tool_name == "orchestrate" and orchestrate_called:
                # Force stop after multiple orchestrate calls - task should be done
                return Success("Task completed via orchestrate.")
            
            if tool_name == "orchestrate":
                orchestrate_called = True
            
            tool_response = await process_tool_call(state, tool_call, on_tool_call)
            messages.append(tool_response)
        
        # After first orchestrate, remind the LLM to stop calling tools and INCLUDE RESULTS
        if orchestrate_called and turn == 0:
            messages.append({
                "role": "system",
                "content": "STOP. The orchestrate tool has been executed. DO NOT call any more tools. CRITICAL: Your next response MUST include the actual results/content discovered by the tools - NEVER just say 'Task completed' or 'Done'. Analyze the tool results and provide a complete answer to the user's question."
            })
    
    return Success("Max turns reached without completion.")


async def run_with_prompt(
    state: UnifiedProviderState,
    prompt: str,
    custom_instructions: str = "",
    max_turns: int = 20,
    on_tool_call: Callable[[str, dict], None] | None = None,
    on_response: Callable[[str], None] | None = None,
    on_token_update: Callable[[int, int, int], None] | None = None,
    existing_messages: list[dict[str, Any]] | None = None
) -> Result[tuple[str, list[dict[str, Any]]], str]:
    """Main entry point for running with a prompt
    
    Returns:
        Success with (response_text, updated_messages) to maintain conversation history
    """
    if existing_messages:
        # Continue existing conversation
        messages = existing_messages.copy()
        messages.append({"role": "user", "content": prompt})
    else:
        # Start fresh conversation
        messages = build_messages(prompt, custom_instructions)
    
    result = await run_agent_loop(state, messages, max_turns, on_tool_call, on_response, on_token_update)
    
    if isinstance(result, Success):
        # Return both the response text and the updated messages for history
        return Success((result.unwrap(), messages))
    else:
        return Failure(result.failure())
