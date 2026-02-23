from typing import Callable, TypeVar
from pydantic import BaseModel
from returns.result import Result

T = TypeVar("T")
E = TypeVar("E")


class ToolResult(BaseModel, frozen=True):
    output: str
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


class ToolDefinition(BaseModel, frozen=True):
    name: str
    description: str
    parameters: dict


class ToolCall(BaseModel, frozen=True):
    id: str
    name: str
    arguments: dict


class Message(BaseModel, frozen=True):
    role: str
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


class AgentConfig(BaseModel, frozen=True):
    model: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    instructions: str | None = None
    sandbox_image: str = "python:3.11-slim"
    max_turns: int = 20


class SandboxConfig(BaseModel, frozen=True):
    image: str = "python:3.11-slim"
    memory_limit: str = "512m"
    cpu_period: int = 100000
    cpu_quota: int = 50000
    timeout: int = 120
    workdir: str = ""  # Empty = use current working directory


class Callbacks(BaseModel, frozen=True):
    on_tool_call: Callable[[str, dict], None] | None = None
    on_response: Callable[[str], None] | None = None


ToolExecutor = Callable[[dict], Result[ToolResult, str]]
ToolSchemaBuilder = Callable[[], ToolDefinition]
