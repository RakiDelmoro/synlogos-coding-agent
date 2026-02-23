import subprocess
from pathlib import Path
from typing import Any
from returns.result import Result, Success, Failure

from src.types import ToolResult
from src.tools.functional_tools import FunctionalTool, make_tool_schema


async def git_status() -> Result[ToolResult, str]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True
        )
        return Success(ToolResult(output=result.stdout or "Not a git repository"))
    except FileNotFoundError:
        return Success(ToolResult(output="Git not installed", error="Git not found"))
    except Exception as e:
        return Failure(str(e))


async def git_diff(target: str = "HEAD") -> Result[ToolResult, str]:
    try:
        result = subprocess.run(
            ["git", "diff", target],
            capture_output=True,
            text=True
        )
        return Success(ToolResult(output=result.stdout or "No changes"))
    except Exception as e:
        return Failure(str(e))


async def git_log(oneline: bool = False, limit: int = 10) -> Result[ToolResult, str]:
    try:
        args = ["git", "log", f"-{limit}"]
        if oneline:
            args.append("--oneline")
        result = subprocess.run(
            args,
            capture_output=True,
            text=True
        )
        return Success(ToolResult(output=result.stdout or "No commits"))
    except Exception as e:
        return Failure(str(e))


async def git_add(files: str = ".") -> Result[ToolResult, str]:
    try:
        result = subprocess.run(
            ["git", "add", files],
            capture_output=True,
            text=True
        )
        return Success(ToolResult(output=f"Staged: {files}"))
    except Exception as e:
        return Failure(str(e))


async def git_commit(message: str) -> Result[ToolResult, str]:
    try:
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True,
            text=True
        )
        return Success(ToolResult(output=result.stdout or result.stderr))
    except Exception as e:
        return Failure(str(e))


async def git_branch() -> Result[ToolResult, str]:
    try:
        result = subprocess.run(
            ["git", "branch", "-a"],
            capture_output=True,
            text=True
        )
        return Success(ToolResult(output=result.stdout or "No branches"))
    except Exception as e:
        return Failure(str(e))


def create_git_status_tool() -> FunctionalTool:
    return FunctionalTool(
        name="git_status",
        description="Check git repository status",
        parameters_schema=make_tool_schema(
            name="git_status",
            description="Check git status",
            properties={},
            required=[]
        ),
        executor=git_status
    )


def create_git_diff_tool() -> FunctionalTool:
    return FunctionalTool(
        name="git_diff",
        description="Show git diff",
        parameters_schema=make_tool_schema(
            name="git_diff",
            description="Show git diff",
            properties={
                "target": {"type": "string", "description": "Target to diff against", "default": "HEAD"}
            },
            required=[]
        ),
        executor=git_diff
    )


def create_git_log_tool() -> FunctionalTool:
    return FunctionalTool(
        name="git_log",
        description="Show git commit history",
        parameters_schema=make_tool_schema(
            name="git_log",
            description="Show git log",
            properties={
                "limit": {"type": "integer", "description": "Number of commits to show", "default": 10},
                "oneline": {"type": "boolean", "description": "Show one line per commit", "default": False}
            },
            required=[]
        ),
        executor=git_log
    )


def create_git_add_tool() -> FunctionalTool:
    return FunctionalTool(
        name="git_add",
        description="Stage files for commit",
        parameters_schema=make_tool_schema(
            name="git_add",
            description="Stage files",
            properties={
                "files": {"type": "string", "description": "Files to stage (default: all)", "default": "."}
            },
            required=[]
        ),
        executor=git_add
    )


def create_git_commit_tool() -> FunctionalTool:
    return FunctionalTool(
        name="git_commit",
        description="Create a git commit",
        parameters_schema=make_tool_schema(
            name="git_commit",
            description="Create commit",
            properties={
                "message": {"type": "string", "description": "Commit message"}
            },
            required=["message"]
        ),
        executor=git_commit
    )


def create_git_branch_tool() -> FunctionalTool:
    return FunctionalTool(
        name="git_branch",
        description="List all git branches",
        parameters_schema=make_tool_schema(
            name="git_branch",
            description="List branches",
            properties={},
            required=[]
        ),
        executor=git_branch
    )


def create_all_git_tools() -> list[FunctionalTool]:
    return [
        create_git_status_tool(),
        create_git_diff_tool(),
        create_git_log_tool(),
        create_git_add_tool(),
        create_git_commit_tool(),
        create_git_branch_tool(),
    ]
