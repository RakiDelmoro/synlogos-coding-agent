from typing import Protocol, TypeVar, runtime_checkable
from returns.result import Result
from .types import ToolResult, ToolDefinition

T = TypeVar("T")


@runtime_checkable
class Tool(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...
    def get_schema(self) -> ToolDefinition: ...
    async def execute(self, **kwargs) -> Result[ToolResult, str]: ...


@runtime_checkable
class HasExecMethods(Protocol):
    async def exec(self, command: str, timeout: int | None = None, workdir: str | None = None) -> Result[ToolResult, str]: ...
    async def exec_code(self, code: str, language: str = "python", timeout: int = 30) -> Result[ToolResult, str]: ...
