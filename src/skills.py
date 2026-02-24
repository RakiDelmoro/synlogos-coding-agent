"""Minimal skill management for Synlogos - Zero config, just works"""

import json
from pathlib import Path
from returns.result import Result, Success, Failure
from rich.console import Console
from rich.panel import Panel


console = Console()

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

# Minimal Ollama-only config
DEFAULT_CONFIG = {
    "$schema": "https://opencode.ai/config.json",
    "theme": "matrix",
    "instructions": ["skills.md"],
    "provider": {
        "ollama": {
            "npm": "@ai-sdk/openai-compatible",
            "options": {"baseURL": "http://localhost:11434/v1"},
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
        urllib.request.urlopen("http://localhost:11434", timeout=2)
        return True
    except:
        return False


def get_available_models() -> list[str]:
    """Get list of available models from Ollama"""
    import urllib.request

    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
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
