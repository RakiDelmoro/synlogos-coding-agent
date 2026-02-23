from dataclasses import dataclass
from typing import Callable, Awaitable
from pathlib import Path
import aiofiles
from returns.result import Result, Success, Failure

from src.types import ToolResult, ToolDefinition
from src.protocols import Tool, HasExecMethods
from src.sandbox.programmatic_tools import execute_programmatic_code


@dataclass(frozen=True)
class FunctionalTool:
    name: str
    description: str
    parameters_schema: dict
    executor: Callable[..., Awaitable[Result[ToolResult, str]]]
    
    def get_schema(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters_schema
        )
    
    async def execute(self, **kwargs) -> Result[ToolResult, str]:
        return await self.executor(**kwargs)


def make_tool_schema(
    name: str,
    description: str,
    properties: dict,
    required: list[str]
) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": required
    }


def make_tool_definition(
    name: str,
    description: str,
    parameters: dict
) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters
        }
    }


async def read_file(path: str, offset: int = 1, limit: int = 2000) -> Result[ToolResult, str]:
    try:
        file_path = Path(path)
        if not file_path.exists():
            return Success(ToolResult(output="", error=f"File not found: {path}"))
        
        async with aiofiles.open(file_path, 'r') as f:
            lines = await f.readlines()
        
        start = max(0, offset - 1)
        end = start + limit
        selected = lines[start:end]
        
        result = "".join(f"{i + offset}: {line}" for i, line in enumerate(selected))
        return Success(ToolResult(output=result))
    except Exception as e:
        return Failure(str(e))


async def write_file(path: str, content: str) -> Result[ToolResult, str]:
    try:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(file_path, 'w') as f:
            await f.write(content)
        
        return Success(ToolResult(output=f"Successfully wrote {len(content)} chars to {path}"))
    except Exception as e:
        return Failure(str(e))


async def edit_file(
    path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False
) -> Result[ToolResult, str]:
    try:
        file_path = Path(path)
        if not file_path.exists():
            return Success(ToolResult(output="", error=f"File not found: {path}"))
        
        async with aiofiles.open(file_path, 'r') as f:
            content = await f.read()
        
        if old_string not in content:
            return Success(ToolResult(output="", error="old_string not found in file"))
        
        count = content.count(old_string)
        new_content = content.replace(old_string, new_string, -1 if replace_all else 1)
        
        async with aiofiles.open(file_path, 'w') as f:
            await f.write(new_content)
        
        return Success(ToolResult(output=f"Replaced {count if replace_all else 1} occurrence(s) in {path}"))
    except Exception as e:
        return Failure(str(e))


def create_file_read_tool() -> FunctionalTool:
    return FunctionalTool(
        name="read_file",
        description="Read the contents of a file from the filesystem",
        parameters_schema=make_tool_schema(
            name="read_file",
            description="Read the contents of a file",
            properties={
                "path": {"type": "string", "description": "Absolute path to the file"},
                "offset": {"type": "integer", "description": "Line to start from (1-indexed)", "default": 1},
                "limit": {"type": "integer", "description": "Max lines to read", "default": 2000}
            },
            required=["path"]
        ),
        executor=read_file
    )


def create_file_write_tool() -> FunctionalTool:
    return FunctionalTool(
        name="write_file",
        description="Write content to a file, creating it if it doesn't exist",
        parameters_schema=make_tool_schema(
            name="write_file",
            description="Write content to a file",
            properties={
                "path": {"type": "string", "description": "Absolute path to the file"},
                "content": {"type": "string", "description": "Content to write"}
            },
            required=["path", "content"]
        ),
        executor=write_file
    )


def create_file_edit_tool() -> FunctionalTool:
    return FunctionalTool(
        name="edit_file",
        description="Edit a file by replacing exact string matches",
        parameters_schema=make_tool_schema(
            name="edit_file",
            description="Edit a file by replacing strings",
            properties={
                "path": {"type": "string", "description": "Absolute path to the file"},
                "old_string": {"type": "string", "description": "String to find and replace"},
                "new_string": {"type": "string", "description": "Replacement string"},
                "replace_all": {"type": "boolean", "description": "Replace all occurrences", "default": False}
            },
            required=["path", "old_string", "new_string"]
        ),
        executor=edit_file
    )


def create_shell_tool(sandbox: HasExecMethods) -> FunctionalTool:
    async def shell_executor(command: str, timeout: int = 120, workdir: str | None = None) -> Result[ToolResult, str]:
        return await sandbox.exec(command, timeout=timeout, workdir=workdir)
    
    return FunctionalTool(
        name="shell",
        description="Execute a shell command in a sandboxed environment",
        parameters_schema=make_tool_schema(
            name="shell",
            description="Execute shell command",
            properties={
                "command": {"type": "string", "description": "Shell command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 120},
                "workdir": {"type": "string", "description": "Working directory"}
            },
            required=["command"]
        ),
        executor=shell_executor
    )


def create_code_tool(sandbox: HasExecMethods) -> FunctionalTool:
    async def code_executor(code: str, language: str = "python", timeout: int = 30) -> Result[ToolResult, str]:
        return await sandbox.exec_code(code, language=language, timeout=timeout)
    
    return FunctionalTool(
        name="execute_code",
        description="Execute Python or JavaScript code in a sandboxed environment",
        parameters_schema=make_tool_schema(
            name="execute_code",
            description="Execute code",
            properties={
                "code": {"type": "string", "description": "Code to execute"},
                "language": {"type": "string", "enum": ["python", "javascript"], "default": "python"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30}
            },
            required=["code"]
        ),
        executor=code_executor
    )


def create_all_tools(sandbox: HasExecMethods) -> list[FunctionalTool]:
    return [
        create_file_read_tool(),
        create_file_write_tool(),
        create_file_edit_tool(),
        create_shell_tool(sandbox),
        create_code_tool(sandbox),
    ]


def create_orchestration_tool(
    available_tools: tuple[FunctionalTool, ...],
    on_tool_call: Callable[[str, dict], None] | None = None
) -> FunctionalTool:
    """
    Create a tool for programmatic tool calling.
    
    Allows the LLM to write Python code that orchestrates multiple tool calls
    without hitting context each time. Intermediate results stay in the code
    execution environment, only the final result is returned.
    """
    async def orchestrate(
        code: str,
        description: str = "",
        timeout: int = 120
    ) -> Result[ToolResult, str]:
        """Execute Python code that can call tools programmatically"""
        
        result = await execute_programmatic_code(
            code=code,
            tools=available_tools,
            timeout=timeout,
            on_tool_call=on_tool_call
        )
        
        if isinstance(result, Success):
            exec_result = result.unwrap()
            
            # Build summary
            output_parts = []
            if exec_result.get("stdout"):
                output_parts.append(exec_result["stdout"])
            
            # Include the final result if present
            final_result = exec_result.get("result")
            if final_result:
                if isinstance(final_result, ToolResult):
                    if final_result.output:
                        output_parts.append(f"\n{final_result.output}")
                    if final_result.error:
                        output_parts.append(f"\nError: {final_result.error}")
                else:
                    output_parts.append(f"\n{final_result}")
            
            # Count tool calls made
            tool_count = exec_result.get("tool_calls", 0)
            if tool_count > 0:
                output_parts.append(f"\n[Executed {tool_count} tool calls programmatically]")
            
            # Check if there's an execution error
            exec_error = exec_result.get("error")
            if exec_error:
                output_parts.append(f"\nExecution error: {exec_error}")
            
            return Success(ToolResult(output="".join(output_parts)))
        else:
            return Failure(result.failure())
    
    return FunctionalTool(
        name="orchestrate",
        description="""Execute Python code that orchestrates tool operations.

CRITICAL: Your code runs INSIDE an async environment. DO NOT use import asyncio, DO NOT use asyncio.run(), DO NOT define async def main(). Just write code that uses await directly.

Use this tool ONCE to complete a task, then respond with text only (no more tool calls).

CRITICAL DISTINCTION:
- "Create/write/save a FILE" → use write_file() → persists on disk
- "Run/test/execute CODE" → use execute_code() → temporary, doesn't save

Available tool functions (use with await):
FILE OPERATIONS:
- await read_file(path, offset=1, limit=2000) -> ToolResult
- await write_file(path, content) -> ToolResult  
- await edit_file(path, old_string, new_string, replace_all=False) -> ToolResult

SEARCH:
- await glob(pattern, path=None) -> ToolResult (returns file list)
- await grep(pattern, path, include=None) -> ToolResult (returns matches)

EXECUTION:
- await shell(command, timeout=120, workdir=None) -> ToolResult
- await execute_code(code, language="python", timeout=30) -> ToolResult

GIT:
- await git_status() -> ToolResult
- await git_diff() -> ToolResult
- await git_log(limit=10) -> ToolResult
- await git_commit(message) -> ToolResult

PARALLEL EXECUTION:
Use asyncio.gather() to run multiple operations in parallel:
    results = await asyncio.gather(*[read_file(f) for f in files])

IMPORTANT:
1. Code runs in async context - use await directly
2. NO import asyncio needed
3. NO async def main() needed  
4. NO asyncio.run() needed
5. Check result.error before using result.output
6. Return via print() or set 'result' variable

Examples:

Read multiple files in parallel:
```python
files = await asyncio.gather(
    read_file("src/types.py"),
    read_file("src/protocols.py")
)
lines = sum(len(f.output.split("\\n")) for f in files if not f.error)
print(f"Total lines: {lines}")
```

Search and process:
```python
# Find all Python files
files_result = await glob("**/*.py")
files = [f.strip() for f in files_result.output.split("\\n") if f.strip()]

# Read them all in parallel
contents = await asyncio.gather(*[read_file(f) for f in files[:5]])
imports = []
for content in contents:
    if not content.error:
        imports.extend([l for l in content.output.split("\\n") if l.startswith("import")])

print(f"Found {len(imports)} import statements")
```

Create a file:
```python
# Create a new module
await write_file("src/new_module.py", "def hello():\\n    return 'world'\\n")

# Verify it was created
result = await read_file("src/new_module.py")
if not result.error:
    print("File created successfully")
    print(result.output)
else:
    print(f"Error: {result.error}")
```

"Create a file" vs "Execute code" - DIFFERENT TOOLS:

Example 1 - Creating a file (persists on disk):
```python
# User says: "Write a hello world program in Rust"
# This CREATES a file - use write_file

# Use escaped newlines in the string
content = "fn main() { println!(\"Hello, world!\"); }"
await write_file("hello.rs", content)
result = await shell("rustc hello.rs && ./hello")
if not result.error:
    print(result.output)
```

Example 2 - Executing code (temporary, doesn't save):
```python
# User says: "Test this Rust code"
# This runs code temporarily - use execute_code

code = "fn main() { println!(\"Hello, world!\"); }"
result = await execute_code(code, language="rust")
if not result.error:
    print(result.output)
```""",
        parameters_schema=make_tool_schema(
            name="orchestrate",
            description="Execute orchestration code",
            properties={
                "code": {
                    "type": "string",
                    "description": "Python code to execute as a single-line JSON string. Use \\n for newlines. Example: \"await write_file('test.txt','hello')\\nprint('done')\". NO actual newlines. NO triple quotes."
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of what this code does",
                    "default": ""
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds",
                    "default": 120
                }
            },
            required=["code"]
        ),
        executor=orchestrate
    )


def create_semantic_search_tool() -> FunctionalTool:
    """Create semantic search tool (vector-based code search)"""
    from src.tools.semantic_search import semantic_search
    
    async def search(query: str, path: str = ".", top_k: int = 5) -> Result[ToolResult, str]:
        return await semantic_search(query, path, top_k)
    
    return FunctionalTool(
        name="semantic_search",
        description="Search codebase semantically using TF-IDF. Finds files related to concepts, not just text matches.",
        parameters_schema=make_tool_schema(
            "semantic_search",
            "Search for code by meaning/concepts, not just exact text. Good for finding related functions, implementations, or patterns.",
            properties={
                "query": {
                    "type": "string",
                    "description": "What you're looking for conceptually (e.g., 'function that handles auth', 'database connection code')"
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in",
                    "default": "."
                },
                "top_k": {
                    "type": "integer", 
                    "description": "Number of results to return",
                    "default": 5
                }
            },
            required=["query"]
        ),
        executor=search
    )
