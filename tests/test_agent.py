"""Tests for Synlogos agent components"""
import os
import pytest
import asyncio
from returns.result import Success, Failure

from src.agent.synlogos import create_synlogos, start_synlogos, run_synlogos
from src.types import AgentConfig
from src.tools.functional_tools import (
    create_file_read_tool,
    create_file_write_tool,
    create_orchestration_tool,
)
from src.sandbox.programmatic_tools import (
    create_programmatic_state,
    execute_programmatic_code,
)


class TestAgentCreation:
    """Test agent factory functions"""
    
    def test_create_synlogos_with_defaults(self):
        result = create_synlogos()
        assert isinstance(result, Success)
        state = result.unwrap()
        assert state.config.model == ""  # Default is empty string
        assert state.sandbox is None
    
    def test_create_synlogos_with_config(self):
        config = AgentConfig(model="test-model", max_turns=10)
        result = create_synlogos(config=config)
        assert isinstance(result, Success)
        state = result.unwrap()
        assert state.config.model == "test-model"


class TestTools:
    """Test individual tools"""
    
    @pytest.mark.asyncio
    async def test_read_file_tool(self, tmp_path):
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("line1\nline2\nline3\n")
        
        tool = create_file_read_tool()
        result = await tool.execute(path=str(test_file))
        
        assert isinstance(result, Success)
        assert "line1" in result.unwrap().output
        assert "line3" in result.unwrap().output
    
    @pytest.mark.asyncio
    async def test_write_file_tool(self, tmp_path):
        test_file = tmp_path / "output.txt"
        tool = create_file_write_tool()
        
        result = await tool.execute(path=str(test_file), content="hello world")
        
        assert isinstance(result, Success)
        assert test_file.exists()
        assert test_file.read_text() == "hello world"


class TestProgrammaticToolCalling:
    """Test programmatic tool calling"""
    
    @pytest.mark.asyncio
    async def test_programmatic_state_creation(self):
        from src.tools.functional_tools import FunctionalTool
        
        tools = (create_file_read_tool(),)
        state = create_programmatic_state("test code", tools)
        
        assert state.code == "test code"
        assert len(state.tools) == 1
        assert state.error is None
    
    @pytest.mark.asyncio
    async def test_execute_programmatic_code_basic(self, tmp_path):
        """Test basic code execution"""
        tools = (create_file_read_tool(),)
        
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\ny = 2\n")
        
        code = f'''
result = await read_file("{test_file}")
if not result.error:
    print("File read successfully")
    print(f"Lines: {{len(result.output.split(chr(10)))}}")
'''
        
        result = await execute_programmatic_code(code, tuple(tools))
        
        assert isinstance(result, Success)
        assert "File read successfully" in result.unwrap()["stdout"]


class TestIntegration:
    """Integration tests - require API key"""
    
    @pytest.mark.skipif(
        not os.environ.get("GROQ_API_KEY"),
        reason="No API key available"
    )
    @pytest.mark.asyncio
    async def test_full_agent_run(self):
        """Test complete agent lifecycle"""
        from src.agent.synlogos import Synlogos
        
        agent = Synlogos()
        
        # Start agent
        start_result = await agent.start()
        assert isinstance(start_result, Success)
        
        # Run a simple prompt
        run_result = await agent.run("What is 2 + 2?")
        assert isinstance(run_result, Success)
        assert "4" in run_result.unwrap()
        
        # Stop agent
        await agent.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
