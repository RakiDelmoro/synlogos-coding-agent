from dataclasses import dataclass
from typing import Callable, Awaitable
from pathlib import Path
import aiofiles
from returns.result import Result, Success, Failure

from src.types import ToolResult, ToolDefinition
from src.protocols import Tool, HasExecMethods


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
