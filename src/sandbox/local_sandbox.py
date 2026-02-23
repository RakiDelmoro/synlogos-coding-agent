import asyncio
import os
from pathlib import Path
from dataclasses import dataclass
from returns.result import Result, Success, Failure

from src.types import ToolResult, SandboxConfig


@dataclass(frozen=True)
class LocalSandboxState:
    config: SandboxConfig
    workdir: Path


def create_local_sandbox(config: SandboxConfig | None = None) -> LocalSandboxState:
    config = config or SandboxConfig()
    workdir = Path(config.workdir) if config.workdir else Path.cwd()
    workdir.mkdir(parents=True, exist_ok=True)
    return LocalSandboxState(config=config, workdir=workdir)


async def start_local_sandbox(state: LocalSandboxState) -> Result[LocalSandboxState, str]:
    state.workdir.mkdir(parents=True, exist_ok=True)
    return Success(state)


async def stop_local_sandbox(state: LocalSandboxState) -> Result[LocalSandboxState, str]:
    return Success(state)


async def exec_in_local_sandbox(
    state: LocalSandboxState,
    command: str,
    timeout: int | None = None,
    workdir: str | None = None
) -> Result[ToolResult, str]:
    try:
        cwd = Path(workdir) if workdir else state.workdir
        cwd.mkdir(parents=True, exist_ok=True)
        
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd)
        )
        
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout or state.config.timeout
        )
        
        output = stdout.decode() if stdout else ""
        error_out = stderr.decode() if stderr else None
        
        return Success(ToolResult(
            output=output,
            error=error_out if proc.returncode != 0 else None
        ))
    except asyncio.TimeoutError:
        return Success(ToolResult(output="", error=f"Command timed out after {timeout}s"))
    except Exception as e:
        return Failure(str(e))


async def exec_code_in_local_sandbox(
    state: LocalSandboxState,
    code: str,
    language: str = "python",
    timeout: int = 30
) -> Result[ToolResult, str]:
    ext = {"python": "py", "javascript": "js"}.get(language, "py")
    runner = {"python": "python3", "javascript": "node"}.get(language, "python3")
    
    code_file = state.workdir / f"_exec.{ext}"
    code_file.write_text(code)
    
    return await exec_in_local_sandbox(state, f"{runner} {code_file}", timeout=timeout)


async def write_to_local_sandbox(
    state: LocalSandboxState,
    path: str,
    content: str
) -> Result[ToolResult, str]:
    try:
        file_path = state.workdir / path.lstrip("/")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return Success(ToolResult(output=f"Wrote {len(content)} chars to {path}"))
    except Exception as e:
        return Failure(str(e))


async def read_from_local_sandbox(
    state: LocalSandboxState,
    path: str
) -> Result[ToolResult, str]:
    try:
        file_path = state.workdir / path.lstrip("/")
        if not file_path.exists():
            return Success(ToolResult(output="", error=f"File not found: {path}"))
        content = file_path.read_text()
        return Success(ToolResult(output=content))
    except Exception as e:
        return Failure(str(e))


class LocalSandbox:
    def __init__(self, config: SandboxConfig | None = None):
        self._state = create_local_sandbox(config)
    
    @property
    def config(self) -> SandboxConfig:
        return self._state.config
    
    @property
    def workdir(self) -> Path:
        return self._state.workdir
    
    async def start(self) -> Result[None, str]:
        result = await start_local_sandbox(self._state)
        if isinstance(result, Success):
            self._state = result.unwrap()
            return Success(None)
        return result
    
    async def stop(self) -> Result[None, str]:
        return Success(None)
    
    async def exec(self, command: str, timeout: int | None = None, workdir: str | None = None) -> Result[ToolResult, str]:
        return await exec_in_local_sandbox(self._state, command, timeout, workdir)
    
    async def exec_code(self, code: str, language: str = "python", timeout: int = 30) -> Result[ToolResult, str]:
        return await exec_code_in_local_sandbox(self._state, code, language, timeout)
    
    async def write_file(self, path: str, content: str) -> Result[ToolResult, str]:
        return await write_to_local_sandbox(self._state, path, content)
    
    async def read_file(self, path: str) -> Result[ToolResult, str]:
        return await read_from_local_sandbox(self._state, path)
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, *args):
        await self.stop()
