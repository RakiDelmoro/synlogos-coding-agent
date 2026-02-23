#!/usr/bin/env python3
"""Debug script to trace agent execution"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agent.synlogos import Synlogos
from src.types import AgentConfig


async def main():
    api_key = os.environ.get("TOGETHER_API_KEY")
    if not api_key:
        print("Error: TOGETHER_API_KEY not set")
        sys.exit(1)
    
    print("=" * 60)
    print("Synlogos Agent Debug")
    print("=" * 60)
    
    config = AgentConfig(max_turns=5)
    
    messages = []
    
    def on_tool_call(name: str, args: dict):
        print(f"\n[TOOL CALL] {name}")
        if 'code' in args:
            print(f"Code:\n{args['code']}")
        else:
            print(f"Args: {args}")
    
    def on_response(text: str):
        if text:
            print(f"\n[LLM RESPONSE] {text[:500]}...")
        messages.append(text)
    
    async with Synlogos(config=config, api_key=api_key) as agent:
        print("\nStarting agent...")
        result = await agent.run(
            "write hello world program in rust",
            on_tool_call=on_tool_call,
            on_response=on_response
        )
        
        print(f"\n{'='*60}")
        print(f"Final result type: {type(result)}")
        if hasattr(result, 'unwrap'):
            print(f"Result: {result.unwrap()[:200] if result.unwrap() else 'None'}")
        
        print(f"\nMessages exchanged: {len(messages)}")
        
        # Check if file was created
        import os
        if os.path.exists("/workspaces/synlogos/hello.rs"):
            print("\n[✓] File created successfully!")
            with open("/workspaces/synlogos/hello.rs") as f:
                print(f"Content:\n{f.read()}")
        else:
            print("\n[✗] File NOT created")


if __name__ == "__main__":
    asyncio.run(main())
