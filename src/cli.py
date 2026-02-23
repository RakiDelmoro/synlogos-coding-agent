#!/usr/bin/env python3
"""Synlogos CLI - Multi-provider, multi-agent AI coding assistant"""
import argparse
import asyncio
import os
import sys
import time
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.table import Table
from returns.result import Success, Failure

from src.config import get_cached_config, list_agent_types, get_agent_info
from src.agent.synlogos import Synlogos
from src.types import AgentConfig
from src.metrics import (
    reset_session_metrics, record_tool_execution, record_user_prompt,
    print_session_summary, get_session_metrics
)


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


def show_startup(cwd: str, provider: str, model: str, agent_type: str | None = None):
    """Display startup banner with current configuration"""
    console.print()
    console.print(f"[bold green]{BANNER}[/bold green]")
    console.print(TAGLINE, justify="center")
    console.print()
    
    # Get agent info
    agent_info = ""
    if agent_type:
        agent_info = f"[bold cyan]Agent:[/] {agent_type}\n"
    
    console.print(Panel(
        f"[bold cyan]Working Directory:[/] {cwd}\n"
        f"[bold cyan]Provider:[/] {provider}\n"
        f"[bold cyan]Model:[/] {model}\n"
        f"{agent_info}"
        f"[bold cyan]Mode:[/] Programmatic Tool Calling\n\n"
        f"[bold]Architecture:[/]\n"
        f"  [green]•[/] LLM writes Python code via `orchestrate` tool\n"
        f"  [green]•[/] All operations execute programmatically\n"
        f"  [green]•[/] Reduced context pollution & token usage\n"
        f"  [green]•[/] Parallel execution via asyncio.gather()\n\n"
        f"[dim]Type 'exit' or 'quit' to end session.[/]",
        title="[bold green]Synlogos AI Coding Agent[/bold green]",
        border_style="green",
        padding=(1, 2)
    ))
    console.print()


def show_token_usage(usage):
    """Display token usage statistics"""
    table = Table(show_header=False, box=None)
    table.add_column("metric", style="dim")
    table.add_column("value", style="cyan")
    table.add_row("Prompt tokens:", f"{usage.prompt_tokens:,}")
    table.add_row("Completion tokens:", f"{usage.completion_tokens:,}")
    table.add_row("Total tokens:", f"{usage.total_tokens:,}")
    console.print(table)


def show_slash_commands():
    """Display available slash commands"""
    console.print()
    console.print("[bold cyan]Available Slash Commands:[/]")
    console.print()
    
    commands = [
        ("/help", "Show this help message"),
        ("/agent [type]", "Switch to a different agent type"),
        ("/agents", "List all available agent types"),
        ("/provider", "Show current provider and model"),
        ("/providers", "List all configured providers"),
        ("/clear", "Clear the screen"),
        ("/tokens", "Show current token usage"),
        ("/metrics", "Show session tool usage metrics"),
        ("/config", "Show current configuration"),
        ("/exit", "Exit the session"),
    ]
    
    for cmd, desc in commands:
        console.print(f"  [green]{cmd:<20}[/] {desc}")
    
    console.print()
    console.print("[dim]You can also type 'exit' or 'quit' to end the session.[/]")
    console.print()


def show_current_config(agent):
    """Show current configuration"""
    console.print()
    console.print("[bold cyan]Current Configuration:[/]")
    console.print()
    console.print(f"  Provider: [green]{agent.provider_name or 'Not started'}[/]")
    console.print(f"  Model: [green]{agent.model_name or 'Not started'}[/]")
    if agent.token_usage:
        console.print(f"  Tokens used: [green]{agent.token_usage.total_tokens:,}[/]")
    console.print()


def clear_screen():
    """Clear the terminal screen"""
    console.clear()
    console.print("[dim]Screen cleared.[/]")
    console.print()


async def process_slash_command(cmd: str, args: list[str], agent) -> tuple[bool, bool]:
    """
    Process a slash command.
    
    Returns:
        (handled, should_exit) - whether command was handled and if we should exit
    """
    cmd = cmd.lower()
    
    if cmd in ("/help", "/h", "/?"):
        show_slash_commands()
        return True, False
    
    elif cmd == "/clear":
        clear_screen()
        return True, False
    
    elif cmd == "/tokens":
        if agent.token_usage:
            show_token_usage(agent.token_usage)
        else:
            console.print("[dim]No token usage yet.[/]")
        return True, False
    
    elif cmd == "/metrics":
        console.print()
        console.print(Panel(
            Markdown(get_session_metrics().get_summary()),
            title="[bold green]📊 Session Metrics[/bold green]",
            border_style="green"
        ))
        return True, False
    
    elif cmd == "/provider":
        console.print()
        console.print(f"[bold cyan]Current Provider:[/] [green]{agent.provider_name or 'Not started'}[/]")
        console.print(f"[bold cyan]Current Model:[/] [green]{agent.model_name or 'Not started'}[/]")
        console.print()
        return True, False
    
    elif cmd == "/providers":
        show_providers()
        return True, False
    
    elif cmd == "/agents" or cmd == "/agent" and not args:
        show_agent_types()
        return True, False
    
    elif cmd == "/config":
        show_current_config(agent)
        return True, False
    
    elif cmd == "/agent" and args:
        # Note: Agent switching would require restarting the agent
        # For now, just inform the user
        new_agent_type = args[0]
        console.print()
        console.print(f"[yellow]To switch to '{new_agent_type}' agent, restart with:[/]")
        console.print(f"[dim]  synlogos --agent {new_agent_type}[/]")
        console.print()
        return True, False
    
    elif cmd in ("/exit", "/quit", "/q"):
        return True, True
    
    else:
        console.print(f"[red]Unknown command: {cmd}[/]")
        console.print("[dim]Type /help for available commands[/]")
        return True, False


SLASH_COMMANDS = {
    "/help": "Show help message",
    "/agent": "Switch agent type (requires restart)",
    "/agents": "List all available agents",
    "/provider": "Show current provider and model",
    "/providers": "List all configured providers",
    "/clear": "Clear the screen",
    "/tokens": "Show token usage",
    "/config": "Show current configuration",
    "/exit": "Exit the session",
}


def show_agent_types():
    """Display available agent types"""
    console.print()
    console.print("[bold]Available Agent Types:[/]")
    console.print()
    
    agent_types = list_agent_types()
    if not agent_types:
        console.print("[dim]No agent types configured. Check synlogos.json[/]")
        return
    
    for agent_type in sorted(agent_types):
        info = get_agent_info(agent_type)
        if info:
            console.print(f"  [green]•[/] [bold]{agent_type}[/] - {info['provider']}/{info['model']}")
            if info['has_custom_instructions']:
                console.print(f"    [dim]Custom instructions: Yes[/]")
    
    console.print()


def show_providers():
    """Display available providers"""
    config_result = get_cached_config()
    if isinstance(config_result, Failure):
        console.print(f"[red]Error loading config: {config_result.failure()}[/]")
        return
    
    config = config_result.unwrap()
    console.print()
    console.print("[bold]Configured Providers:[/]")
    console.print()
    
    for name, provider in config.providers.items():
        model_count = len(provider.models)
        console.print(f"  [green]•[/] [bold]{name}[/] - {model_count} model(s)")
        console.print(f"    [dim]Base URL: {provider.base_url}[/]")
        for model_name in provider.models:
            console.print(f"      - {model_name}")
    
    console.print(f"\n[dim]Default model: {config.default_model}[/]")
    console.print()


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Synlogos - Multi-provider AI coding agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  synlogos                          # Run with default agent
  synlogos --agent code             # Use the code agent
  synlogos --agent explore          # Use the explore agent
  synlogos --agent architect        # Use the architect agent
  synlogos --list-agents           # Show available agents
  synlogos --list-providers        # Show configured providers
        """
    )
    
    parser.add_argument(
        "--agent",
        type=str,
        help="Agent type to use (explore, code, architect, etc.)"
    )
    
    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="List available agent types and exit"
    )
    
    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="List configured providers and exit"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to synlogos.json config file"
    )
    
    parser.add_argument(
        "--max-turns",
        type=int,
        default=30,
        help="Maximum conversation turns (default: 30)"
    )
    
    return parser.parse_args()


async def run_async():
    """Main run loop"""
    args = parse_args()
    
    # Handle info-only commands
    if args.list_agents:
        show_agent_types()
        return 0
    
    if args.list_providers:
        show_providers()
        return 0
    
    # Load configuration
    config_result = get_cached_config()
    if isinstance(config_result, Failure):
        console.print(f"[red]Error: {config_result.failure()}[/]")
        console.print("[dim]Make sure synlogos.json exists in the current directory.[/]")
        return 1
    
    config = config_result.unwrap()
    
    # Get agent configuration
    agent_type = args.agent
    if agent_type and agent_type not in config.agent_types:
        console.print(f"[red]Error: Unknown agent type: {agent_type}[/]")
        console.print("[dim]Use --list-agents to see available agents[/]")
        return 1
    
    # Get the provider and model for display
    if agent_type:
        agent_config = config.agent_types[agent_type]
        display_provider = agent_config.provider
        display_model = agent_config.model
    else:
        # Use default
        parts = config.default_model.split("/")
        if len(parts) >= 2:
            display_provider = parts[0]
            display_model = "/".join(parts[1:])
        else:
            display_provider = "unknown"
            display_model = config.default_model
    
    cwd = os.getcwd()
    show_startup(cwd, display_provider, display_model, agent_type)
    
    # Create agent config
    agent_config = AgentConfig(
        max_turns=args.max_turns
    )
    
    try:
        # Reset metrics at start of session
        reset_session_metrics()
        
        async with Synlogos(
            config=agent_config,
            agent_type=agent_type
        ) as agent:
            
            # Show actual provider info
            console.print(f"[dim]Connected to: {agent.provider_name}/{agent.model_name}[/dim]")
            console.print()
            
            # Live token usage display
            from rich.live import Live
            from rich.text import Text
            
            current_tokens = {"prompt": 0, "completion": 0, "total": 0}
            
            def create_token_status():
                """Create a compact token usage status"""
                return Text.assemble(
                    ("Tokens: ", "dim"),
                    (f"{current_tokens['total']:,}", "cyan"),
                    (" (", "dim"),
                    (f"↑{current_tokens['prompt']:,}", "green"),
                    (" ", "dim"),
                    (f"↓{current_tokens['completion']:,}", "magenta"),
                    (")", "dim")
                )
            
            def on_token_update(prompt: int, completion: int, total: int):
                """Callback to update token display"""
                current_tokens["prompt"] = prompt
                current_tokens["completion"] = completion
                current_tokens["total"] = total
            
            while True:
                try:
                    # Show token status before prompt
                    if current_tokens["total"] > 0:
                        console.print(create_token_status())
                    
                    prompt = Prompt.ask("[bold blue]You[/bold blue]")
                    
                    # Record user prompt in metrics
                    record_user_prompt()
                    
                    # Handle slash commands
                    if prompt.startswith("/"):
                        parts = prompt.split(maxsplit=1)
                        cmd = parts[0]
                        args = parts[1].split() if len(parts) > 1 else []
                        
                        handled, should_exit = await process_slash_command(cmd, args, agent)
                        if should_exit:
                            if agent.token_usage:
                                console.print()
                                show_token_usage(agent.token_usage)
                            # Show session metrics
                            console.print()
                            console.print(Panel(
                                Markdown(get_session_metrics().get_summary()),
                                title="[bold green]📊 Session Metrics[/bold green]",
                                border_style="green"
                            ))
                            console.print("\n[yellow]Goodbye![/]")
                            break
                        if handled:
                            continue
                    
                    # Handle regular exit commands
                    if prompt.lower() in ("exit", "quit", "q"):
                        if agent.token_usage:
                            console.print()
                            show_token_usage(agent.token_usage)
                        console.print("\n[yellow]Goodbye![/]")
                        break
                    
                    if not prompt.strip():
                        continue
                    
                    console.print()
                    
                    tool_count = 0
                    has_shown_reasoning = False
                    last_response_text = ""
                    
                    def on_tool_call(name: str, args: dict):
                        nonlocal tool_count, has_shown_reasoning
                        tool_count += 1
                        
                        # Record metrics for tool call
                        record_tool_execution(name, success=True)
                        
                        # If we haven't shown reasoning yet, show it now before tools
                        if not has_shown_reasoning and last_response_text:
                            has_shown_reasoning = True
                            console.print()
                            console.print(Panel(
                                Markdown(last_response_text),
                                title="[bold blue]🤔 Reasoning[/bold blue]",
                                border_style="blue",
                                padding=(1, 1)
                            ))
                        
                        # Show tool execution header
                        console.print()
                        console.print(f"[bold cyan]⚡ Executing:[/bold cyan] [yellow]{name}[/yellow]")
                        
                        if name == "write_file":
                            console.print(f"[dim]   Writing to:[/dim] {args.get('path', '?')}")
                        elif name == "read_file":
                            console.print(f"[dim]   Reading:[/dim] {args.get('path', '?')}")
                        elif name == "edit_file":
                            console.print(f"[dim]   Editing:[/dim] {args.get('path', '?')}")
                        elif name == "shell":
                            cmd = args.get('command', '')
                            console.print(f"[dim]   Command:[/dim] {cmd[:80]}{'...' if len(cmd) > 80 else ''}")
                        elif name == "execute_code":
                            lang = args.get('language', 'python')
                            console.print(f"[dim]   Language:[/dim] {lang}")
                        elif name == "grep":
                            console.print(f"[dim]   Pattern:[/dim] '{args.get('pattern', '?')}'")
                        elif name == "glob":
                            console.print(f"[dim]   Pattern:[/dim] {args.get('pattern', '?')}")
                        elif name == "orchestrate":
                            code = args.get('code', '')
                            desc = args.get('description', '')
                            if desc:
                                console.print(f"[dim]   Description:[/dim] {desc}")
                            console.print()
                            console.print(Panel(
                                f"[dim]{code[:500]}{'...' if len(code) > 500 else ''}[/dim]",
                                title="[yellow]📝 Generated Code[/yellow]",
                                border_style="yellow"
                            ))
                        elif name.startswith("git_"):
                            pass
                        
                        console.print("[dim]   Running...[/dim]")
                    
                    def on_tool_result(name: str, args: dict, output: str):
                        """Display tool results as they complete"""
                        if output and output.strip():
                            # Show truncated output for large results
                            max_len = 500
                            display_output = output[:max_len] + "..." if len(output) > max_len else output
                            
                            console.print()
                            console.print(Panel(
                                f"[dim]{display_output}[/dim]",
                                title=f"[green]📤 {name} Result[/green]",
                                border_style="green"
                            ))
                    
                    def on_response(text: str):
                        nonlocal last_response_text
                        # Store the response text but don't display it yet
                        # We'll decide later whether it's reasoning or the final answer
                        last_response_text = text
                    
                    result = await agent.run(prompt, on_tool_call, on_response, on_token_update, on_tool_result)
                    
                    if isinstance(result, Failure):
                        console.print(f"\n[red]❌ Error: {result.failure()}[/]")
                    elif isinstance(result, Success):
                        final_text = result.unwrap()
                        
                        if tool_count > 0:
                            # Tools were executed - show reasoning was already shown, now show final result
                            console.print(f"\n[green]✓[/] [dim]Completed {tool_count} tool call(s)[/dim]")
                            if final_text:
                                console.print()
                                console.print(Panel(
                                    Markdown(final_text),
                                    title="[bold green]✅ Final Result[/bold green]",
                                    border_style="green",
                                    padding=(1, 2)
                                ))
                        else:
                            # No tools executed - this IS the response, not reasoning
                            if final_text:
                                console.print()
                                console.print(Panel(
                                    Markdown(final_text),
                                    title="[bold cyan]💬 Response[/bold cyan]",
                                    border_style="cyan",
                                    padding=(1, 2)
                                ))
                    
                    console.print()
                    
                except KeyboardInterrupt:
                    console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/]")
                except Exception as e:
                    console.print(f"\n[red]Error: {e}[/]")
                    
    except Exception as e:
        console.print(f"[red]Failed to start: {e}[/]")
        sys.exit(1)


def run():
    """Entry point for synlogos CLI - wraps the async run function"""
    try:
        exit_code = asyncio.run(run_async())
        sys.exit(exit_code or 0)
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/]")
        sys.exit(0)


if __name__ == "__main__":
    run()
