#!/usr/bin/env python3
import asyncio
import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.table import Table
from returns.result import Success, Failure

from src.types import AgentConfig
from src.agent.synlogos import Synlogos


console = Console()


BANNER = """
███████╗██╗   ██╗███╗   ██╗██╗      ██████╗  ██████╗  ██████╗ ███████╗
██╔════╝╚██╗ ██╔╝████╗  ██║██║     ██╔═══██╗██╔════╝ ██╔═══██╗██╔════╝
███████╗ ╚████╔╝ ██╔██╗ ██║██║     ██║   ██║██║  ███╗██║   ██║███████╗
╚════██║  ╚██╔╝  ██║╚██╗██║██║     ██║   ██║██║   ██║██║   ██║╚════██║
███████║   ██║   ██║ ╚████║███████╗╚██████╔╝╚██████╔╝╚██████╔╝███████║
╚══════╝   ╚═╝   ╚═╝  ╚═══╝╚══════╝ ╚═════╝  ╚═════╝  ╚═════╝╚══════╝
"""
TAGLINE = "[dim italic]In the beginning was the Code, and the Code was with the AI, and the Code was AI.[/]"


def show_startup(cwd: str):
    console.print()
    console.print(f"[bold green]{BANNER}[/bold green]")
    console.print(TAGLINE, justify="center")
    console.print()
    console.print(Panel(
        f"[bold cyan]Working Directory:[/] {cwd}\n"
        f"[bold cyan]Model:[/] meta-llama/Llama-3.3-70B-Instruct-Turbo\n"
        f"[bold cyan]Context:[/] 128K tokens\n\n"
        f"[bold]Available Tools:[/]\n"
        f"  [green]•[/] read_file, write_file, edit_file\n"
        f"  [green]•[/] shell, execute_code\n"
        f"  [green]•[/] glob, grep\n"
        f"  [green]•[/] git_status, git_diff, git_log, git_commit\n\n"
        f"[dim]Type 'exit' or 'quit' to end session.[/]",
        title="[bold green]Synlogos AI Coding Agent[/bold green]",
        border_style="green",
        padding=(1, 2)
    ))
    console.print()


def show_token_usage(usage):
    table = Table(show_header=False, box=None)
    table.add_column("metric", style="dim")
    table.add_column("value", style="cyan")
    table.add_row("Prompt tokens:", f"{usage.prompt_tokens:,}")
    table.add_row("Completion tokens:", f"{usage.completion_tokens:,}")
    table.add_row("Total tokens:", f"{usage.total_tokens:,}")
    console.print(table)


async def run():
    api_key = os.environ.get("TOGETHER_API_KEY")
    if not api_key:
        console.print("[red]Error: TOGETHER_API_KEY environment variable not set[/red]")
        console.print("[dim]Get your key at https://api.together.xyz/settings/api-keys[/dim]")
        sys.exit(1)
    
    cwd = os.getcwd()
    show_startup(cwd)
    
    config = AgentConfig(
        model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        max_turns=30
    )
    
    try:
        async with Synlogos(config=config, api_key=api_key) as agent:
            while True:
                try:
                    prompt = Prompt.ask("[bold blue]You[/bold blue]")
                    
                    if prompt.lower() in ("exit", "quit", "q"):
                        if agent._state.provider_state:
                            console.print()
                            show_token_usage(agent._state.provider_state.token_usage)
                        console.print("\n[yellow]Goodbye![/yellow]")
                        break
                    
                    if not prompt.strip():
                        continue
                    
                    console.print()
                    
                    tool_count = 0
                    
                    def on_tool_call(name: str, args: dict):
                        nonlocal tool_count
                        tool_count += 1
                        console.print(f"[dim]│[/dim] [yellow]●[/yellow] {name}", end="")
                        if name == "write_file":
                            console.print(f"[dim] → {args.get('path', '?')}[/dim]")
                        elif name == "read_file":
                            console.print(f"[dim] → {args.get('path', '?')}[/dim]")
                        elif name == "edit_file":
                            console.print(f"[dim] → {args.get('path', '?')}[/dim]")
                        elif name == "shell":
                            cmd = args.get('command', '')[:50]
                            console.print(f"[dim] → {cmd}...[/dim]")
                        elif name == "execute_code":
                            console.print(f"[dim] ({args.get('language', 'python')})[/dim]")
                        elif name == "grep":
                            console.print(f"[dim] → '{args.get('pattern', '?')}'[/dim]")
                        elif name == "glob":
                            console.print(f"[dim] → {args.get('pattern', '?')}[/dim]")
                        elif name.startswith("git_"):
                            console.print()
                        else:
                            console.print()
                    
                    def on_response(text: str):
                        console.print()
                        console.print(Panel(
                            Markdown(text),
                            title="[bold green]Synlogos[/bold green]",
                            border_style="green",
                            padding=(1, 1)
                        ))
                    
                    result = await agent.run(prompt, on_tool_call, on_response)
                    
                    if isinstance(result, Failure):
                        console.print(f"\n[red]Error: {result.failure()}[/red]")
                    elif tool_count > 0:
                        console.print(f"\n[dim]Completed {tool_count} tool call(s)[/dim]")
                    
                    console.print()
                    
                except KeyboardInterrupt:
                    console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
                except Exception as e:
                    console.print(f"\n[red]Error: {e}[/red]")
                    
    except Exception as e:
        console.print(f"[red]Failed to start: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run())
