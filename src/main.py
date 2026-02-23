import asyncio
import os
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from returns.result import Failure

from src.agent.functional_agent import FunctionalAgent
from src.types import AgentConfig


console = Console()


async def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        console.print("[red]Error: GROQ_API_KEY environment variable not set[/red]")
        console.print("[dim]Get your free key at https://console.groq.com/keys[/dim]")
        return
    
    console.print(Panel.fit(
        "[bold green]Synlogos AI Coding Agent[/bold green]\n"
        "Powered by TogetherAI with Docker sandbox\n"
        "[dim]Functional architecture with returns library[/dim]",
        border_style="green"
    ))
    
    config = AgentConfig(
        model="llama-3.3-70b-versatile",
        max_turns=30
    )
    
    async with FunctionalAgent(config=config, api_key=api_key) as agent:
        console.print("\n[cyan]Sandbox initialized. Ready for tasks.[/cyan]")
        console.print("[dim]Type 'exit' to quit[/dim]\n")
        
        while True:
            try:
                prompt = console.input("[bold blue]You:[/bold blue] ")
                
                if prompt.lower() in ("exit", "quit"):
                    console.print("\n[yellow]Shutting down...[/yellow]")
                    break
                
                if not prompt.strip():
                    continue
                
                console.print()
                
                def on_tool_call(name: str, args: dict):
                    console.print(f"[dim]→ Tool: {name}({args})[/dim]")
                
                def on_response(text: str):
                    console.print(Panel(Markdown(text), border_style="green", title="[bold]Assistant[/bold]"))
                
                result = await agent.run(
                    prompt=prompt,
                    on_tool_call=on_tool_call,
                    on_response=on_response
                )
                
                if isinstance(result, Failure):
                    console.print(f"\n[red]Error: {result.failure()}[/red]")
                
                console.print()
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")


if __name__ == "__main__":
    asyncio.run(main())
