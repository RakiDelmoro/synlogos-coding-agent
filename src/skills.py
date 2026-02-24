"""Minimal skill management for Synlogos - Zero config, just works"""

import json
import os
from pathlib import Path
from returns.result import Result, Success, Failure
from rich.console import Console
from rich.panel import Panel


console = Console()

# Get Ollama host from environment or use default
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "localhost:11434")
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}/v1"

# Simple default skill - no generation needed
DEFAULT_SKILL = """# AI Coding Assistant

## Who I Am
I am your AI coding assistant. I help you write, edit, and understand code.

## How I Work
I use the tools available to read files, run commands, and write code. I think step by step.

## How I Communicate
I am direct and clear. I show code when helpful, explain when needed.

## My Standards
Working code over perfect code. Simple solutions over clever ones.

## What I Expect
Tell me what you want to achieve. I'll help you get there.

## My Reminders
- Working code today beats perfect code never
- Simple is better than clever
- Ask if something is unclear
"""

# Minimal Ollama-only config - uses OLLAMA_HOST from environment
DEFAULT_CONFIG = {
    "$schema": "https://opencode.ai/config.json",
    "theme": "matrix",
    "instructions": ["skills.md"],
    "provider": {
        "ollama": {
            "npm": "@ai-sdk/openai-compatible",
            "options": {"baseURL": OLLAMA_BASE_URL},
            "models": {
                "qwen3:8b": {"model": "qwen3:8b"},
                "qwen3:14b": {"model": "qwen3:14b"},
                "deepseek-coder:6.7b": {"model": "deepseek-coder:6.7b"},
                "llama3.1:8b": {"model": "llama3.1:8b"},
            },
        }
    },
    "model": "ollama/qwen3:8b",
    "agent": {
        "explore": {
            "model": "ollama/qwen3:8b",
            "instructions": "You are a fast file explorer. Find and read files quickly.",
        },
        "code": {
            "model": "ollama/qwen3:8b",
            "instructions": "You are a coding assistant. Write, edit, and debug code.",
        },
        "test": {
            "model": "ollama/qwen3:8b",
            "instructions": "You are a testing specialist. Run tests and find bugs.",
        },
        "review": {
            "model": "ollama/qwen3:8b",
            "instructions": "You are a code reviewer. Check code for issues.",
        },
        "memory": {
            "model": "ollama/qwen3:8b",
            "instructions": "You manage memory.md. Keep it concise and useful.",
        },
    },
}

SKILLS_FILE = Path("skills.md")
CONFIG_FILE = Path("synlogos.json")


def get_skills_path() -> Path:
    return Path.cwd() / SKILLS_FILE


def get_config_path() -> Path:
    return Path.cwd() / CONFIG_FILE


def skills_exists() -> bool:
    return get_skills_path().exists()


def config_exists() -> bool:
    return get_config_path().exists()


def check_ollama() -> bool:
    """Quick check if Ollama is running"""
    import urllib.request

    try:
        urllib.request.urlopen(f"http://{OLLAMA_HOST}", timeout=2)
        return True
    except:
        return False


def get_available_models() -> list[str]:
    """Get list of available models from Ollama"""
    import urllib.request

    try:
        req = urllib.request.Request(f"http://{OLLAMA_HOST}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            return [m.get("name", "") for m in data.get("models", [])]
    except:
        return []


def ensure_setup() -> Result[bool, str]:
    """Ensure setup files exist - creates minimal defaults"""
    skills_path = get_skills_path()
    config_path = get_config_path()

    # Create default skills.md if missing
    if not skills_path.exists():
        try:
            skills_path.write_text(DEFAULT_SKILL)
        except Exception as e:
            return Failure(f"Cannot create skills.md: {e}")

    # Create default synlogos.json if missing
    if not config_path.exists():
        try:
            config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
        except Exception as e:
            return Failure(f"Cannot create synlogos.json: {e}")

    return Success(True)


def get_skill_instructions() -> str:
    """Get skill instructions - returns simple default if no skills"""
    path = get_skills_path()
    if path.exists():
        return path.read_text()
    return DEFAULT_SKILL


def pull_ollama_model(model_name: str) -> Result[bool, str]:
    """Pull a model from Ollama"""
    import urllib.request
    import time

    console.print(f"[dim]Pulling {model_name}...[/dim]")

    try:
        req = urllib.request.Request(
            f"http://{OLLAMA_HOST}/api/pull",
            data=json.dumps({"name": model_name}).encode(),
            headers={"Content-Type": "application/json"},
        )

        # Stream the response to show progress
        with urllib.request.urlopen(req, timeout=600) as response:
            # Read line by line for streaming updates
            buffer = b""
            while True:
                chunk = response.read(1)
                if not chunk:
                    break
                buffer += chunk
                if b"\n" in buffer:
                    lines = buffer.split(b"\n")
                    for line in lines[:-1]:
                        if line:
                            try:
                                data = json.loads(line.decode())
                                status = data.get("status", "")
                                if "completed" in status:
                                    console.print(
                                        f"[green]✓ {model_name} pulled successfully[/green]"
                                    )
                                    return Success(True)
                            except:
                                pass
                    buffer = lines[-1]

            console.print(f"[green]✓ {model_name} pulled successfully[/green]")
            return Success(True)

    except Exception as e:
        return Failure(f"Failed to pull {model_name}: {e}")


def run_model_onboarding() -> Result[str, str]:
    """Interactive model selection and setup"""
    console.print()
    console.print(
        Panel.fit(
            "[bold green]Welcome to Synlogos![/bold green]\nChoose your AI model to get started.",
            border_style="green",
        )
    )
    console.print()

    # Check if Ollama is running
    if not check_ollama():
        console.print(
            Panel(
                "[red]❌ Ollama is not running[/red]\n\n"
                "Please start Ollama first:\n"
                "  [dim]ollama serve[/dim]",
                title="Setup Required",
                border_style="red",
            )
        )
        return Failure("Ollama not running")

    console.print("[green]✓ Ollama is running[/green]")
    console.print()

    # Get available models
    available_models = get_available_models()

    # Recommended models
    RECOMMENDED_MODELS = [
        ("qwen3:8b", "Fast & good for most tasks (Recommended)"),
        ("qwen3:14b", "Better quality, slower"),
        ("qwen3:32b", "Best quality, slowest"),
        ("deepseek-coder:6.7b", "Code-focused, fast"),
        ("deepseek-coder:33b", "Best for complex coding"),
        ("llama3.1:8b", "Alternative option"),
    ]

    if available_models:
        console.print("[bold]Your installed models:[/bold]")
        for model in available_models:
            console.print(f"  [green]•[/] {model}")
        console.print()

    # Ask user to select or type any model
    console.print("[bold cyan]Choose your AI model:[/bold cyan]")
    console.print(
        "[dim]You can pick from recommended models or type any model name you want.[/dim]"
    )
    console.print()

    for i, (model, desc) in enumerate(RECOMMENDED_MODELS, 1):
        installed = "[green](installed)" if model in available_models else "[dim](not installed)"
        console.print(f"  {i}. {model} - {desc} {installed}[/dim]")

    console.print()
    console.print("  Or type any model name (e.g., 'codellama:7b', 'mistral:latest')")
    console.print()

    from rich.prompt import Prompt

    choice = Prompt.ask("Enter number or model name", default="1")

    # Check if input is a number (selection) or model name
    try:
        choice_num = int(choice)
        if 1 <= choice_num <= len(RECOMMENDED_MODELS):
            model_name = RECOMMENDED_MODELS[choice_num - 1][0]
        else:
            model_name = RECOMMENDED_MODELS[0][0]
    except ValueError:
        # User typed a model name directly
        model_name = choice.strip()

    # Check if model needs to be pulled
    if model_name not in available_models:
        console.print()
        console.print(f"[yellow]{model_name} not found. Pulling now...[/yellow]")
        console.print("[dim]This may take a few minutes depending on your connection.[/dim]")

        result = pull_ollama_model(model_name)
        if isinstance(result, Failure):
            console.print(f"[red]Failed to pull model: {result.failure()}[/red]")
            return Failure(result.failure())

    # Update config with selected model
    config_path = get_config_path()
    try:
        if config_path.exists():
            with open(config_path, "r") as f:
                config = json.load(f)
        else:
            config = DEFAULT_CONFIG.copy()

        # Update the default model
        config["model"] = f"ollama/{model_name}"

        # Add model to provider if not exists
        if model_name not in config["provider"]["ollama"]["models"]:
            config["provider"]["ollama"]["models"][model_name] = {"model": model_name}

        # Save updated config
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        console.print()
        console.print(f"[green]✓ Setup complete! Using {model_name}[/green]")
        console.print(f"[dim]You can change this anytime with:[/dim] [cyan]synlogos --setup[/cyan]")

        return Success(model_name)

    except Exception as e:
        return Failure(f"Failed to update config: {e}")


def show_ollama_status():
    """Show Ollama status"""
    import urllib.request

    console.print()

    if not check_ollama():
        console.print(
            Panel(
                "[red]Ollama is not running[/red]\n\nStart it with:\n  ollama serve",
                title="Ollama Status",
                border_style="red",
            )
        )
        return

    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            models = data.get("models", [])

            if models:
                model_list = "\n".join([f"  • {m.get('name', 'unknown')}" for m in models[:10]])
                console.print(
                    Panel(
                        f"[green]✓ Ollama is running[/green]\n\n"
                        f"Available models ({len(models)}):\n{model_list}",
                        title="Ollama Status",
                        border_style="green",
                    )
                )
            else:
                console.print(
                    Panel(
                        "[yellow]Ollama is running but no models found[/yellow]\n\n"
                        "Pull a model:\n"
                        "  ollama pull qwen3:8b",
                        title="Ollama Status",
                        border_style="yellow",
                    )
                )
    except Exception as e:
        console.print(
            Panel(
                f"[red]Error checking Ollama: {e}[/red]", title="Ollama Status", border_style="red"
            )
        )


def display_current_skill():
    """Display current skill"""
    path = get_skills_path()
    if path.exists():
        console.print()
        console.print(
            Panel(path.read_text()[:500] + "\n...", title="Current Skill", border_style="green")
        )
    else:
        console.print("[dim]Using default skill[/dim]")


def reset_to_defaults():
    """Reset config to defaults"""
    skills_path = get_skills_path()
    config_path = get_config_path()

    try:
        skills_path.write_text(DEFAULT_SKILL)
        config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
        console.print("[green]✓ Reset to defaults[/green]")
        return Success(True)
    except Exception as e:
        return Failure(f"Cannot reset: {e}")
