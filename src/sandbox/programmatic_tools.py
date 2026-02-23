"""
Programmatic Tool Calling - Functional implementation for Synlogos.
Allows LLM to write code that orchestrates multiple tool calls
without hitting context each time.
"""
import asyncio
import json
from dataclasses import dataclass
from typing import Callable, Any
from returns.result import Result, Success, Failure
from returns.pipeline import pipe
from returns.pointfree import bind

from src.types import ToolResult
from src.protocols import Tool


@dataclass(frozen=True)
class ToolCallRecord:
    """Immutable record of a tool call within programmatic code"""
    name: str
    args: tuple
    kwargs: dict


@dataclass(frozen=True)
class ProgrammaticExecutionState:
    """Immutable state for programmatic code execution"""
    code: str
    tools: tuple[Tool, ...]
    tool_map: dict[str, Tool]
    execution_log: tuple[ToolCallRecord, ...]
    stdout: str
    stderr: str
    error: str | None
    timeout: int


@dataclass(frozen=True)
class ExecutionConfig:
    """Configuration for code execution"""
    timeout: int = 120


def create_programmatic_state(
    code: str,
    tools: tuple[Tool, ...],
    timeout: int = 120
) -> ProgrammaticExecutionState:
    """Create initial state for programmatic execution"""
    return ProgrammaticExecutionState(
        code=code,
        tools=tools,
        tool_map={t.name: t for t in tools},
        execution_log=(),
        stdout="",
        stderr="",
        error=None,
        timeout=timeout
    )


def create_tool_wrappers(
    state: ProgrammaticExecutionState,
    on_tool_call: Callable[[str, dict], None] | None = None,
    execution_log: list | None = None
) -> dict[str, Callable]:
    """Create async wrapper functions for each tool"""
    
    # Use mutable list for execution tracking (state is immutable)
    log = execution_log if execution_log is not None else []
    
    def make_wrapper(tool_name: str, tool_def: Tool) -> Callable:
        # Get parameter names from schema for positional arg mapping
        schema = getattr(tool_def, 'parameters_schema', {})
        properties = schema.get('properties', {})
        param_names = list(properties.keys())
        
        async def wrapper(*args, **kwargs) -> ToolResult:
            # Convert positional args to kwargs if provided
            if args and param_names:
                for i, arg in enumerate(args):
                    if i < len(param_names):
                        kwargs[param_names[i]] = arg
            
            # Log the tool call
            log.append(ToolCallRecord(
                name=tool_name,
                args=args,
                kwargs=kwargs
            ))
            
            # Notify callback if provided
            if on_tool_call:
                on_tool_call(tool_name, kwargs)
            
            # Execute tool - tools use kwargs only
            result = await tool_def.execute(**kwargs)
            
            if isinstance(result, Success):
                return result.unwrap()
            else:
                raise Exception(f"Tool {tool_name} failed: {result.failure()}")
        
        return wrapper
    
    # Build wrapper dict
    wrappers = {}
    for name, tool_def in state.tool_map.items():
        wrappers[name] = make_wrapper(name, tool_def)
    
    return wrappers


def build_execution_namespace(
    state: ProgrammaticExecutionState,
    on_tool_call: Callable[[str, dict], None] | None = None,
    execution_log: list | None = None
) -> dict[str, Any]:
    """Build namespace for code execution with tool access"""
    
    # Capture output in a mutable list (since state is immutable)
    output_buffer = []
    
    def capture_print(*args, **kwargs):
        sep = kwargs.get('sep', ' ')
        end = kwargs.get('end', '\n')
        text = sep.join(str(a) for a in args) + end
        output_buffer.append(text)
    
    # Get captured output as a closure
    def get_output():
        return ''.join(output_buffer)
    
    namespace = {
        "__builtins__": {
            "print": capture_print,
            "len": len,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "sum": sum,
            "min": min,
            "max": max,
            "sorted": sorted,
            "list": list,
            "dict": dict,
            "set": set,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "type": type,
            "isinstance": isinstance,
            "hasattr": hasattr,
            "getattr": getattr,
            "locals": locals,
            "Exception": Exception,
        },
        "asyncio": asyncio,
        "json": json,
        "ToolResult": ToolResult,
        "__get_output__": get_output,  # Store reference to get output
        "__execution_log__": execution_log,  # Store reference to log
        **create_tool_wrappers(state, on_tool_call, execution_log)
    }
    
    return namespace


def wrap_code_in_async_function(code: str) -> str:
    """Wrap user code in an async function for execution"""
    indented_code = "\n".join(f"    {line}" for line in code.split("\n"))
    return f"""async def __synlogos_main():
{indented_code}
    return locals().get('result', None)
"""


async def execute_programmatic_code(
    code: str,
    tools: tuple[Tool, ...],
    timeout: int = 120,
    on_tool_call: Callable[[str, dict], None] | None = None
) -> Result[dict[str, Any], str]:
    """
    Execute Python code that can call tools programmatically.
    
    The code runs in an isolated environment where tool calls are intercepted
    and executed without hitting the LLM context.
    
    Returns Result with stdout, execution log, and final result.
    """
    try:
        # Create initial state
        state = create_programmatic_state(code, tools, timeout)
        
        # Create mutable execution log (state is immutable)
        execution_log: list[ToolCallRecord] = []
        
        # Build execution namespace
        namespace = build_execution_namespace(state, on_tool_call, execution_log)
        
        # Wrap code in async function
        wrapped_code = wrap_code_in_async_function(code)
        
        # Execute wrapped code in namespace
        exec(wrapped_code, namespace)
        
        # Get and run the main function
        main_func = namespace["__synlogos_main"]
        result = await asyncio.wait_for(main_func(), timeout=timeout)
        
        # Get captured output
        get_output = namespace.get("__get_output__", lambda: "")
        captured_stdout = get_output()
        
        return Success({
            "stdout": captured_stdout,
            "stderr": "",
            "result": result,
            "tool_calls": len(execution_log)
        })
        
    except asyncio.TimeoutError:
        return Failure(f"Code execution timed out after {timeout} seconds")
    except Exception as e:
        return Failure(f"Code execution error: {str(e)}")


def build_orchestration_prompt(available_tools: list[str]) -> str:
    """Build prompt teaching LLM how to use programmatic tool calling"""
    tools_str = "\n".join(f"  - await {name}(...)" for name in available_tools)
    
    return f"""You can use programmatic tool calling to orchestrate multiple operations.

When you need to perform multiple tool operations, write Python code that:
1. Calls tools using `await` syntax (they're async functions)
2. Processes results within the code
3. Returns only the final result using `print()` or setting `result`

Available async tool functions:
{tools_str}

Example - read multiple files and summarize:
```python
file1 = await read_file("/path/to/file1.py")
file2 = await read_file("/path/to/file2.py")

if not file1.error and not file2.error:
    total_lines = len(file1.output.split("\\n")) + len(file2.output.split("\\n"))
    print(f"Total lines: {{total_lines}}")
else:
    print("Error reading files")
```

Important:
- ALWAYS use `await` when calling tools
- Process results in code, don't return raw tool outputs
- Only the final printed output or `result` variable is shown to user
- Use `asyncio.gather()` for parallel execution: `results = await asyncio.gather(*tasks)`"""
