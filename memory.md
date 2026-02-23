# Memory

## Current Project
Synlogos — Multi-provider AI Coding Agent with JSON-based configuration. Supports opencode.ai (free), ollama (local), togetherai via unified OpenAI-compatible API. Multiple agent types: explore, grep, summarize, plan, code, architect, web_search, memory. Slash commands (/help, /agents, /tokens, etc.) for runtime control.

## Active Problems
- None

## Solved Problems & How We Fixed Them
[2026-02-23] Added thinking visibility → Enhanced CLI to show LLM reasoning before tool execution with 🤔 Thinking panel, improved tool call display with ⚡ Executing headers, and ✅ Final Result panel
[2026-02-23] JSON parsing of multi-line code → LLM generated code with actual newlines and unescaped quotes in JSON strings. Fixed clean_tool_arguments() to detect code parameter and properly escape newlines/quotes
[2026-02-23] System prompt improvements → Added explicit templates and SUCCESS/FAILURE requirements to prevent hallucinations
[2026-02-23] Files not being created via orchestrate → Three issues: (1) wrapper passed *args to execute() but tools use **kwargs only, (2) missing `locals` builtin, (3) positional args weren't mapped to kwargs. Fixed wrapper to convert positional to kwargs, added locals builtin
[2026-02-23] Orchestrate not writing files → Tool results weren't captured; added result extraction to output and system prompt examples
[2026-02-23] Infinite orchestrate loop → Added guardrails: track orchestrate calls, limit to one per task, system reminder after first call
[2026-02-23] OOP to FP refactoring → Used returns library for Result monads, frozen Pydantic models, pure functions
[2026-02-23] Migrated to Groq → Switched from TogetherAI to Groq (free tier, faster inference, same Llama-3.3-70B model)
[2026-02-23] Multi-provider support → Added unified provider layer supporting opencode.ai (free), ollama (local), togetherai via OpenAI-compatible API
[2026-02-23] JSON config → Moved configuration to synlogos.json with provider configs, models, and agent types
[2026-02-23] Agent not creating files → Improved system prompt to distinguish write_file vs execute_code
[2026-02-23] Programmatic Tool Calling → Implemented Anthropic's PTC: LLM writes code that orchestrates tool calls without hitting context each time
[2026-02-23] Slash commands → Added /help, /agents, /provider, /tokens, /clear, /config, /exit commands for runtime control

## Patterns We've Discovered
- Thinking visibility: Show LLM reasoning before tool calls with clear UI sections
- State threading: Pass immutable state through pure functions
- Result monads: Success/Failure for explicit error handling
- Factory functions: create_tool(), create_agent() pattern
- Dynamic system prompt: Inject cwd at runtime for portability
- Tool composition: Combine file + shell + code + git tools
- Programmatic Tool Calling: LLM writes code → tools execute in sandbox → only final result to context
- Tool loop guardrails: Track tool calls, prevent repeats, add completion reminders
- Result propagation: Capture tool return values, not just stdout, to surface success/failure to user

## Mistakes We Won't Repeat
- Don't use curry decorator with async functions
- Always distinguish write_file (persistent) from execute_code (temporary)

## My Preferences Learned
- Language: Python with functional patterns
- Error handling: Result monads
- Tools: File ops, shell, code exec, glob, grep, git integration, orchestrate (PTC)
- CLI: Rich library for beautiful output
- State: Immutable dataclasses
