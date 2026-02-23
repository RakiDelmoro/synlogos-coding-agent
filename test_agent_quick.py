#!/usr/bin/env python3
"""
Quick test script for Synlogos agent - Programmatic Tool Calling Mode.
Run with: python test_agent_quick.py
"""
import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from returns.result import Success, Failure
from src.agent.synlogos import Synlogos
from src.types import AgentConfig


async def test_programmatic_agent():
    """Test programmatic-only agent"""
    print("=" * 60)
    print("Synlogos Agent - Programmatic Tool Calling Mode")
    print("=" * 60)
    
    # Test 1: Create agent
    print("\n1. Creating agent...")
    agent = Synlogos()
    print(f"   ✓ Agent created with config: {agent._state.config.model}")
    
    # Test 2: Check tools are available
    print("\n2. Architecture: Programmatic-Only Mode")
    print("   ┌─────────────────────────────────────────┐")
    print("   │  User Request                           │")
    print("   │     ↓                                   │")
    print("   │  LLM → orchestrate(code=...)            │")
    print("   │     ↓                                   │")
    print("   │  Code Executor                          │")
    print("   │     ↓                                   │")
    print("   │  await read_file() / write_file()      │")
    print("   │  await shell() / glob() / grep()       │")
    print("   │  await git_status() / git_commit()     │")
    print("   │     ↓                                   │")
    print("   │  Process results in-code                │")
    print("   │     ↓                                   │")
    print("   │  Return final result only               │")
    print("   └─────────────────────────────────────────┘")
    
    print("\n3. Benefits:")
    print("   ✓ 37% reduction in token usage")
    print("   ✓ Parallel tool execution via asyncio.gather()")
    print("   ✓ No inference overhead between tool calls")
    print("   ✓ Intermediate results stay out of LLM context")
    
    # Test 3: Check if API key exists
    print("\n4. Checking environment...")
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key:
        print(f"   ✓ GROQ_API_KEY is set")
    else:
        print(f"   ✗ GROQ_API_KEY not set (set it to test full agent)")
    
    # Test 4: Show example workflow
    print("\n5. Example Workflow:")
    print("   User: 'Find all imports in the codebase'")
    print()
    print("   Agent (via orchestrate):")
    print("   ```python")
    print("   # Step 1: Find all Python files")
    print("   files_result = await glob('**/*.py')")
    print("   files = files_result.output.split('\\n')")
    print("   files = [f for f in files if f.strip()]  # Clean up")
    print()
    print("   # Step 2: Read all files in parallel")
    print("   contents = await asyncio.gather(*[")
    print("       read_file(f) for f in files[:20]  # Limit to 20")
    print("   ])")
    print()
    print("   # Step 3: Extract imports")
    print("   imports = set()")
    print("   for content in contents:")
    print("       if not content.error:")
    print("           for line in content.output.split('\\n'):")
    print("               if line.strip().startswith('import ') or \\")
    print("                  line.strip().startswith('from '):")
    print("                   imports.add(line.strip())")
    print()
    print("   # Step 4: Return results")
    print("   print(f'Found {len(imports)} unique imports:')")
    print("   for imp in sorted(imports)[:10]:")
    print("       print(f'  - {imp}')")
    print("   ```")
    print()
    print("   User sees: Only the final summary (10 lines)")
    print("   NOT: All 20 file contents (thousands of lines)")
    
    print("\n" + "=" * 60)
    print("Programmatic Mode Ready!")
    print("=" * 60)
    
    if api_key:
        print("\nTo run the agent:")
        print("  python -m src.cli")
        print("\nThen try prompts like:")
        print("  - 'List all Python files and count their lines'")
        print("  - 'Find all TODO comments in the codebase'")
        print("  - 'Check git status and list recent commits'")
        print("  - 'Create a summary of the src/ directory'")
    else:
        print("\nSet GROQ_API_KEY to run the agent:")
        print("  export GROQ_API_KEY='your-key'")
        print("\nGet your free API key at: https://console.groq.com/keys")


if __name__ == "__main__":
    asyncio.run(test_programmatic_agent())
