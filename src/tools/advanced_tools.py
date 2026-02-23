import fnmatch
import re
from pathlib import Path
from typing import Any
from returns.result import Result, Success, Failure

from src.types import ToolResult, ToolDefinition
from src.tools.functional_tools import FunctionalTool, make_tool_schema


async def glob_search(pattern: str, path: str = ".") -> Result[ToolResult, str]:
    try:
        search_path = Path(path)
        if not search_path.exists():
            return Success(ToolResult(output="", error=f"Path not found: {path}"))
        
        matches = []
        for p in search_path.rglob(pattern):
            if p.is_file():
                matches.append(str(p.relative_to(search_path)))
        
        if not matches:
            return Success(ToolResult(output=f"No files matching '{pattern}'"))
        
        matches.sort()
        return Success(ToolResult(output="\n".join(matches)))
    except Exception as e:
        return Failure(str(e))


async def grep_search(
    pattern: str,
    path: str = ".",
    include: str = "*",
    ignore_case: bool = False
) -> Result[ToolResult, str]:
    try:
        search_path = Path(path)
        if not search_path.exists():
            return Success(ToolResult(output="", error=f"Path not found: {path}"))
        
        flags = re.IGNORECASE if ignore_case else 0
        try:
            regex = re.compile(pattern, flags)
        except re.error:
            return Success(ToolResult(output="", error=f"Invalid regex: {pattern}"))
        
        matches = []
        files_to_search = []
        
        for p in search_path.rglob("*"):
            if p.is_file() and fnmatch.fnmatch(p.name, include):
                if ".git" in p.parts or "node_modules" in p.parts or "__pycache__" in p.parts:
                    continue
                files_to_search.append(p)
        
        for file_path in files_to_search[:100]:
            try:
                content = file_path.read_text(errors="ignore")
                for i, line in enumerate(content.splitlines(), 1):
                    if regex.search(line):
                        rel_path = file_path.relative_to(search_path)
                        matches.append(f"{rel_path}:{i}: {line.strip()[:200]}")
                        if len(matches) >= 200:
                            break
            except Exception:
                continue
            if len(matches) >= 200:
                break
        
        if not matches:
            return Success(ToolResult(output=f"No matches found for '{pattern}'"))
        
        return Success(ToolResult(output="\n".join(matches)))
    except Exception as e:
        return Failure(str(e))


def create_glob_tool() -> FunctionalTool:
    return FunctionalTool(
        name="glob",
        description="Find files matching a pattern (e.g., '**/*.py' for all Python files)",
        parameters_schema=make_tool_schema(
            name="glob",
            description="Find files by pattern",
            properties={
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (e.g., '**/*.py', 'src/**/*.ts', '*.json')"
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in",
                    "default": "."
                }
            },
            required=["pattern"]
        ),
        executor=glob_search
    )


def create_grep_tool() -> FunctionalTool:
    return FunctionalTool(
        name="grep",
        description="Search for regex pattern in files. Shows file:line:content for each match.",
        parameters_schema=make_tool_schema(
            name="grep",
            description="Search file contents",
            properties={
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for"
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in",
                    "default": "."
                },
                "include": {
                    "type": "string",
                    "description": "File pattern to include (e.g., '*.py', '*.ts')",
                    "default": "*"
                },
                "ignore_case": {
                    "type": "boolean",
                    "description": "Case insensitive search",
                    "default": False
                }
            },
            required=["pattern"]
        ),
        executor=grep_search
    )
