# Memory

## Current Project
Synlogos — Professional AI Coding Agent. Functional architecture, TogetherAI provider, local sandbox.

## Active Problems
- None currently

## Solved Problems & How We Fixed Them
[2026-02-23] OOP to FP refactoring → Used returns library for Result monads, frozen Pydantic models, pure functions
[2026-02-23] Model availability error → Changed default model to Llama-3.3-70B-Instruct-Turbo (serverless)
[2026-02-23] Agent not creating files → Improved system prompt to distinguish write_file vs execute_code

## Patterns We've Discovered
- State threading: Pass immutable state through pure functions
- Result monads: Success/Failure for explicit error handling
- Factory functions: create_tool(), create_agent() pattern
- Dynamic system prompt: Inject cwd at runtime for portability
- Tool composition: Combine file + shell + code + git tools

## Mistakes We Won't Repeat
- Don't use curry decorator with async functions
- Always distinguish write_file (persistent) from execute_code (temporary)

## My Preferences Learned
- Language: Python with functional patterns
- Error handling: Result monads
- Tools: File ops, shell, code exec, glob, grep, git integration
- CLI: Rich library for beautiful output
- State: Immutable dataclasses
