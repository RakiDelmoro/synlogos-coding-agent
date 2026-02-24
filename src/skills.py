"""Skills management for Synlogos - AI-powered persona generation using TinySkills technique (Ollama-only)"""

import json
import os
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field
from returns.result import Result, Success, Failure
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table


console = Console()

SKILLS_FILE = Path("skills.md")
CONFIG_FILE = Path("synlogos.json")

# Ollama-only skills template
SKILLS_TEMPLATE = """# {skill_name}

## Who I Am
{who_i_am}

## How I Work
{how_i_work}

## How I Communicate
{how_i_communicate}

## My Standards
{my_standards}

## What I Expect From You
{what_i_expect}

## My Reminders to You
{my_reminders}

---

*This skill was generated based on your preferences. You can regenerate it by running `synlogos --setup`*
"""

# Ollama-only models - no cloud providers
OLLAMA_MODELS = {
    1: ("ollama/qwen3:8b", "Qwen3 8B (Fast, good for most tasks)"),
    2: ("ollama/qwen3:14b", "Qwen3 14B (Better quality, slower)"),
    3: ("ollama/qwen3:32b", "Qwen3 32B (Best quality, slowest)"),
    4: ("ollama/llama3.1:8b", "Llama 3.1 8B (Alternative option)"),
    5: ("ollama/deepseek-coder:6.7b", "DeepSeek Coder 6.7B (Coding focused)"),
    6: ("ollama/deepseek-coder:33b", "DeepSeek Coder 33B (Best for complex coding)"),
}

# All agents use Ollama models
AGENT_TYPES = {
    "explore": {
        "description": "Fast file and codebase explorer",
        "lightweight": True,
        "model": "ollama/qwen3:8b",
        "instructions": "You are a fast file and codebase explorer. Search, read, summarize, and map out files, directories, and symbols. Keep responses concise and factual.",
    },
    "grep": {
        "description": "Search specialist",
        "lightweight": True,
        "model": "ollama/qwen3:8b",
        "instructions": "You are a search specialist. Find patterns, usages, imports, and references across the codebase quickly and accurately.",
    },
    "summarize": {
        "description": "Content summarizer",
        "lightweight": True,
        "model": "ollama/qwen3:8b",
        "instructions": "You summarize files, diffs, changelogs, and error logs into clear, brief descriptions.",
    },
    "plan": {
        "description": "Planning and analysis agent",
        "lightweight": False,
        "model": "ollama/qwen3:14b",
        "instructions": "You are a planning agent. Deeply analyze the task and codebase context provided, identify edge cases, dependencies, and risks, then produce a clear ordered step-by-step plan before any code is written.",
    },
    "code": {
        "description": "Primary coding agent",
        "lightweight": False,
        "model": "ollama/deepseek-coder:33b",
        "instructions": "You are the primary coding agent. Write, edit, refactor, and debug code with high accuracy. Handle complex multi-file changes, architecture decisions, and difficult bugs.",
    },
    "architect": {
        "description": "Senior software architect",
        "lightweight": False,
        "model": "ollama/qwen3:14b",
        "instructions": "You are a senior software architect. Design systems, plan large refactors, choose technologies, and reason about scalability and maintainability.",
    },
    "web_search": {
        "description": "Web search specialist",
        "lightweight": False,
        "model": "ollama/qwen3:8b",
        "instructions": "You are a web search specialist. Retrieve accurate, up-to-date information from the web. Summarize results concisely, cite sources, and handle ambiguity carefully.",
    },
    "memory": {
        "description": "Memory management agent",
        "lightweight": False,
        "model": "ollama/qwen3:8b",
        "instructions": "You are the memory agent. Your only job is to keep memory.md compact, accurate, and useful.",
    },
    "test": {
        "description": "Testing specialist",
        "lightweight": True,
        "model": "ollama/qwen3:8b",
        "instructions": "You are a testing specialist. Write and run tests, analyze coverage, find edge cases.",
    },
    "review": {
        "description": "Code reviewer",
        "lightweight": True,
        "model": "ollama/qwen3:8b",
        "instructions": "You are a code reviewer. Review code for bugs, style issues, and best practices.",
    },
    "security": {
        "description": "Security analyst",
        "lightweight": False,
        "model": "ollama/qwen3:14b",
        "instructions": "You are a security analyst. Analyze code for security vulnerabilities and best practices.",
    },
    "docs": {
        "description": "Documentation writer",
        "lightweight": True,
        "model": "ollama/qwen3:8b",
        "instructions": "You are a documentation writer. Write clear documentation, docstrings, and README files.",
    },
}


@dataclass
class Skill:
    """A skill/persona definition"""

    name: str
    who_i_am: str
    how_i_work: str
    how_i_communicate: str
    my_standards: str
    what_i_expect: str
    my_reminders: str
    recommended_agents: list[str] = field(default_factory=list)
    preferred_model: str = "ollama/qwen3:8b"


def get_skills_path() -> Path:
    return Path.cwd() / SKILLS_FILE


def get_config_path() -> Path:
    return Path.cwd() / CONFIG_FILE


def skills_exists() -> bool:
    return get_skills_path().exists()


def config_exists() -> bool:
    return get_config_path().exists()


def is_setup_complete() -> bool:
    return skills_exists() and config_exists()


def check_ollama_running() -> bool:
    """Check if Ollama is running locally"""
    import urllib.request

    try:
        urllib.request.urlopen("http://localhost:11434", timeout=2)
        return True
    except:
        return False


def parse_skills(content: str) -> Result[Skill, str]:
    lines = content.split("\n")
    skill_name = "Default"
    sections = {
        "who_i_am": "",
        "how_i_work": "",
        "how_i_communicate": "",
        "my_standards": "",
        "what_i_expect": "",
        "my_reminders": "",
    }
    current_section = None
    current_content = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            skill_name = stripped.replace("# ", "").strip()
            continue
        if stripped.startswith("## "):
            if current_section and current_content:
                section_key = current_section.lower().replace(" ", "_")
                if section_key in sections:
                    sections[section_key] = "\n".join(current_content).strip()
            current_section = stripped.replace("## ", "").strip()
            current_content = []
        elif current_section and stripped and not stripped.startswith("#"):
            current_content.append(line)

    if current_section and current_content:
        section_key = current_section.lower().replace(" ", "_")
        if section_key in sections:
            sections[section_key] = "\n".join(current_content).strip()

    return Success(
        Skill(
            name=skill_name,
            who_i_am=sections.get("who_i_am", ""),
            how_i_work=sections.get("how_i_work", ""),
            how_i_communicate=sections.get("how_i_communicate", ""),
            my_standards=sections.get("my_standards", ""),
            what_i_expect=sections.get("what_i_expect", ""),
            my_reminders=sections.get("my_reminders", ""),
        )
    )


def load_skills() -> Result[Skill, str]:
    skills_path = get_skills_path()
    if not skills_path.exists():
        return Failure(f"Skills file not found: {skills_path}")
    try:
        with open(skills_path, "r") as f:
            content = f.read()
        return parse_skills(content)
    except Exception as e:
        return Failure(f"Error reading skills file: {e}")


def select_ollama_model() -> str:
    """Select Ollama model"""
    console.print()
    console.print("[bold cyan]Select your Ollama model:[/bold cyan]")
    console.print("[dim]Make sure Ollama is running: ollama serve[/dim]")
    console.print()

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="cyan", width=4)
    table.add_column("Model", style="green")
    table.add_column("Description", style="dim")

    for num, (model_id, description) in OLLAMA_MODELS.items():
        table.add_row(str(num), model_id.replace("ollama/", ""), description)

    console.print(table)
    console.print()

    # Check if Ollama is running
    if not check_ollama_running():
        console.print("[yellow]⚠️  Ollama doesn't appear to be running![/yellow]")
        console.print("[dim]Start it with: ollama serve[/dim]")
        console.print()

    choice = IntPrompt.ask(
        "[bold blue]Enter model number[/bold blue]",
        default=1,
        show_default=True,
    )

    if choice in OLLAMA_MODELS:
        return OLLAMA_MODELS[choice][0]
    else:
        console.print("[yellow]Invalid choice, using default model[/yellow]")
        return "ollama/qwen3:8b"


class OllamaSkillGenerator:
    """Generate skill using Ollama LLM"""

    def __init__(self, model: str):
        self.model = model.replace("ollama/", "")
        self.responses = {}

    def _ask_question(self, question: str, context: str = "") -> str:
        """Ask Ollama a single question"""
        import urllib.request
        import urllib.error

        system_prompt = """You are a persona designer for an AI coding assistant.
Answer the question thoughtfully and concisely (2-4 sentences).
Be specific, actionable, and authentic. Focus on practical behaviors, not generic advice."""

        user_prompt = f"{context}\n\nQuestion: {question}\n\nAnswer concisely in 2-4 sentences:"

        data = json.dumps(
            {
                "model": self.model,
                "prompt": user_prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 300,
                },
            }
        ).encode()

        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=data,
                headers={"Content-Type": "application/json"},
            )

            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode())
                return result.get("response", "").strip()
        except urllib.error.URLError:
            console.print(
                "[red]❌ Cannot connect to Ollama. Make sure it's running: ollama serve[/red]"
            )
            return ""
        except Exception as e:
            console.print(f"[dim red]Ollama error: {e}[/dim red]")
            return ""

    def generate_persona(self, user_description: str) -> dict[str, str]:
        """Generate persona using multiple Ollama queries"""

        console.print()
        console.print("[dim]Generating your personalized AI assistant with Ollama...[/dim]")
        console.print()

        context = f'Creating an AI coding assistant persona based on: "{user_description}"'

        # Phase 1: Core Identity
        questions_phase1 = [
            (
                "identity",
                "Who are you? Describe your role, personality, and core identity as an AI coding assistant.",
            ),
            ("approach", "How do you approach coding tasks? What's your methodology and process?"),
            ("style", "How do you communicate with the user? What's your tone and style?"),
        ]

        console.print("[dim cyan]Phase 1/3: Understanding your identity...[/dim cyan]")
        for key, question in questions_phase1:
            self.responses[key] = self._ask_question(question, context)
            if self.responses[key]:
                console.print(f"  [dim green]✓[/dim green] [dim]{key} captured[/dim]")
            else:
                console.print(f"  [dim red]✗[/dim red] [dim]{key} failed[/dim]")

        # Phase 2: Standards & Expectations
        questions_phase2 = [
            (
                "standards",
                "What are your coding standards? What do you value in code quality and engineering practices?",
            ),
            (
                "expectations",
                "What do you expect from the user? How should they interact with you for best results?",
            ),
        ]

        console.print()
        console.print("[dim cyan]Phase 2/3: Defining standards...[/dim cyan]")
        for key, question in questions_phase2:
            self.responses[key] = self._ask_question(question, context)
            if self.responses[key]:
                console.print(f"  [dim green]✓[/dim green] [dim]{key} captured[/dim]")
            else:
                console.print(f"  [dim red]✗[/dim red] [dim]{key} failed[/dim]")

        # Phase 3: Principles
        questions_phase3 = [
            (
                "reminders",
                "What are 3-4 key principles or reminders that guide your work? Make them memorable.",
            ),
        ]

        console.print()
        console.print("[dim cyan]Phase 3/3: Synthesizing principles...[/dim cyan]")
        for key, question in questions_phase3:
            self.responses[key] = self._ask_question(question, context)
            if self.responses[key]:
                console.print(f"  [dim green]✓[/dim green] [dim]{key} captured[/dim]")
            else:
                console.print(f"  [dim red]✗[/dim red] [dim]{key} failed[/dim]")

        return {
            "who_i_am": self.responses.get(
                "identity", "I am your AI coding assistant, ready to help you write better code."
            ),
            "how_i_work": self.responses.get(
                "approach",
                "I work carefully and methodically, breaking down problems into manageable steps.",
            ),
            "how_i_communicate": self.responses.get(
                "style",
                "I communicate clearly and concisely, explaining my reasoning when helpful.",
            ),
            "my_standards": self.responses.get(
                "standards", "I value working, readable code that follows best practices."
            ),
            "what_i_expect": self.responses.get(
                "expectations",
                "I expect you to share your goals and ask questions when something is unclear.",
            ),
            "my_reminders": self.responses.get(
                "reminders",
                "Simple solutions are better than clever ones. Working code today beats perfect code never.",
            ),
        }


def determine_recommended_agents(user_description: str) -> list[str]:
    """Determine agents based on user intent keywords"""
    user_lower = user_description.lower()

    keywords_to_agents = {
        "teach": ["explore", "code", "architect", "docs"],
        "learn": ["explore", "code", "architect", "docs"],
        "mentor": ["explore", "code", "architect", "docs"],
        "explain": ["explore", "code", "architect", "docs"],
        "fast": ["explore", "code", "test", "grep"],
        "quick": ["explore", "code", "test", "grep"],
        "rapid": ["explore", "code", "test", "grep"],
        "prototype": ["explore", "code", "test", "grep"],
        "review": ["review", "security", "test", "grep"],
        "check": ["review", "security", "test", "grep"],
        "audit": ["review", "security", "test", "grep"],
        "security": ["review", "security", "test", "grep"],
        "pair": ["explore", "code", "plan", "architect"],
        "collaborate": ["explore", "code", "plan", "architect"],
        "document": ["docs", "summarize", "explore"],
        "doc": ["docs", "summarize", "explore"],
        "test": ["test", "review", "code", "explore"],
        "debug": ["test", "review", "code", "explore"],
        "bug": ["test", "review", "code", "explore"],
    }

    recommended = set()
    for keyword, agents in keywords_to_agents.items():
        if keyword in user_lower:
            recommended.update(agents)

    if not recommended:
        recommended = {"explore", "code", "plan", "test"}

    return list(recommended)


def generate_skill_with_ollama(user_description: str, model: str) -> Result[Skill, str]:
    """Generate skill using Ollama LLM"""

    try:
        generator = OllamaSkillGenerator(model)
        persona_data = generator.generate_persona(user_description)

        skill_name = user_description[:50]
        if len(user_description) > 50:
            skill_name += "..."

        skill = Skill(
            name=skill_name,
            who_i_am=persona_data["who_i_am"],
            how_i_work=persona_data["how_i_work"],
            how_i_communicate=persona_data["how_i_communicate"],
            my_standards=persona_data["my_standards"],
            what_i_expect=persona_data["what_i_expect"],
            my_reminders=persona_data["my_reminders"],
            recommended_agents=determine_recommended_agents(user_description),
            preferred_model=model,
        )

        return Success(skill)

    except Exception as e:
        return Failure(f"Ollama generation failed: {e}")


def save_skills(skill: Skill) -> Result[Path, str]:
    path = get_skills_path()
    content = SKILLS_TEMPLATE.format(
        skill_name=skill.name,
        who_i_am=skill.who_i_am,
        how_i_work=skill.how_i_work,
        how_i_communicate=skill.how_i_communicate,
        my_standards=skill.my_standards,
        what_i_expect=skill.what_i_expect,
        my_reminders=skill.my_reminders,
    )

    try:
        if path.exists():
            backup_path = path.with_suffix(".md.backup")
            backup_path.write_text(path.read_text())
        with open(path, "w") as f:
            f.write(content)
        return Success(path)
    except Exception as e:
        return Failure(f"Error saving skills file: {e}")


def generate_config(skill: Skill, model: str) -> dict:
    """Generate Ollama-only synlogos.json config"""
    agent_config = {}

    for agent_name in skill.recommended_agents:
        if agent_name in AGENT_TYPES:
            agent_info = AGENT_TYPES[agent_name]
            agent_config[agent_name] = {
                "model": agent_info["model"],
                "instructions": agent_info["instructions"],
            }

    if "memory" not in agent_config:
        agent_config["memory"] = {
            "model": "ollama/qwen3:8b",
            "instructions": AGENT_TYPES["memory"]["instructions"],
        }

    # Ollama-only config - no cloud providers
    return {
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
                    "qwen3:32b": {"model": "qwen3:32b"},
                    "llama3.1:8b": {"model": "llama3.1:8b"},
                    "deepseek-coder:6.7b": {"model": "deepseek-coder:6.7b"},
                    "deepseek-coder:33b": {"model": "deepseek-coder:33b"},
                },
            }
        },
        "model": model,
        "agent": agent_config,
    }


def save_config(config: dict) -> Result[Path, str]:
    path = get_config_path()
    try:
        if path.exists():
            backup_path = path.with_suffix(".json.backup")
            backup_path.write_text(path.read_text())
        with open(path, "w") as f:
            json.dump(config, f, indent=2)
        return Success(path)
    except Exception as e:
        return Failure(f"Error saving config file: {e}")


def run_onboarding() -> Result[tuple[Skill, dict], str]:
    """Run Ollama-only onboarding"""
    console.print()
    console.print(
        Panel.fit(
            "[bold green]Welcome to Synlogos (Ollama Edition)![/bold green]\n"
            "Let's create your personalized AI coding assistant using local models.",
            border_style="green",
        )
    )
    console.print()

    # Check if Ollama is running
    if not check_ollama_running():
        console.print("[red]❌ Ollama is not running![/red]")
        console.print()
        console.print("[dim]To set up Synlogos, you need Ollama installed and running:[/dim]")
        console.print("  1. Install Ollama: [green]https://ollama.com[/green]")
        console.print("  2. Start Ollama: [green]ollama serve[/green]")
        console.print("  3. Pull a model: [green]ollama pull qwen3:8b[/green]")
        console.print()
        console.print("[yellow]Please start Ollama and try again.[/yellow]")
        return Failure("Ollama not running")

    console.print("[green]✓ Ollama is running[/green]")
    console.print()

    console.print("[cyan]What would you like your AI assistant to be?[/cyan]")
    console.print("[dim]Examples:[/dim]")
    console.print("  • A senior engineer who mentors me through complex refactors")
    console.print("  • A fast coding assistant that helps me prototype quickly")
    console.print("  • A careful reviewer who checks my code for bugs")
    console.print("  • A pair programmer who helps me learn best practices")
    console.print()

    user_description = Prompt.ask("[bold blue]Describe your ideal AI assistant[/bold blue]")

    if not user_description.strip():
        console.print("[yellow]Using default: helpful AI coding assistant[/yellow]")
        user_description = "A helpful AI coding assistant"

    # Select Ollama model
    selected_model = select_ollama_model()

    # Check if model exists
    model_name = selected_model.replace("ollama/", "")
    console.print()
    console.print(f"[dim]Checking if model '{model_name}' is available...[/dim]")

    import urllib.request
    import urllib.error

    try:
        # Try to get model info
        req = urllib.request.Request(
            f"http://localhost:11434/api/show",
            data=json.dumps({"name": model_name}).encode(),
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                console.print(f"[green]✓ Model '{model_name}' is available[/green]")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                console.print(
                    f"[yellow]⚠️  Model '{model_name}' not found. Pulling it now...[/yellow]"
                )
                console.print(f"[dim]This may take a few minutes...[/dim]")

                # Try to pull the model
                pull_req = urllib.request.Request(
                    "http://localhost:11434/api/pull",
                    data=json.dumps({"name": model_name, "stream": False}).encode(),
                    headers={"Content-Type": "application/json"},
                )

                try:
                    with urllib.request.urlopen(pull_req, timeout=300) as response:
                        console.print(f"[green]✓ Model '{model_name}' pulled successfully[/green]")
                except Exception as pull_e:
                    console.print(f"[red]❌ Failed to pull model: {pull_e}[/red]")
                    console.print(f"[dim]Try manually: ollama pull {model_name}[/dim]")
                    return Failure(f"Failed to pull model {model_name}")
    except Exception as e:
        console.print(f"[yellow]⚠️  Could not check model: {e}[/yellow]")

    # Generate skill using Ollama
    result = generate_skill_with_ollama(user_description, selected_model)

    if isinstance(result, Failure):
        return Failure(result.failure())

    skill = result.unwrap()
    config = generate_config(skill, selected_model)

    # Preview
    console.print()
    console.print(
        Panel(
            Markdown(
                f"""## Generated Skill

**Who I Am:** {skill.who_i_am[:100]}...

**How I Work:** {skill.how_i_work[:100]}...

**Recommended Agents:** {", ".join(skill.recommended_agents)}

**Model:** {skill.preferred_model}
"""
            ),
            title="[bold green]Preview[/bold green]",
            border_style="green",
        )
    )

    console.print()
    if Confirm.ask("[bold]Save this configuration?[/bold]"):
        save_result = save_skills(skill)
        config_result = save_config(config)

        if isinstance(save_result, Success) and isinstance(config_result, Success):
            console.print(f"[green]✓ Skill saved to {save_result.unwrap()}[/green]")
            console.print(f"[green]✓ Config saved to {config_result.unwrap()}[/green]")
            console.print()
            console.print("[dim]Your AI assistant is ready![/dim]")
            console.print("[dim]Run 'synlogos' to start using it.[/dim]")
            return Success((skill, config))
        else:
            errors = []
            if isinstance(save_result, Failure):
                errors.append(save_result.failure())
            if isinstance(config_result, Failure):
                errors.append(config_result.failure())
            return Failure("; ".join(errors))
    else:
        if Confirm.ask("Try again with different description?"):
            return run_onboarding()
        return Failure("User cancelled setup")


def ensure_setup() -> Result[tuple[Skill, dict], str]:
    if is_setup_complete():
        skill_result = load_skills()
        if isinstance(skill_result, Success):
            try:
                with open(get_config_path(), "r") as f:
                    config = json.load(f)
                return Success((skill_result.unwrap(), config))
            except Exception as e:
                return Failure(f"Error loading config: {e}")
        return Failure(skill_result.failure())
    return run_onboarding()


def get_skill_instructions() -> str:
    result = load_skills()
    if isinstance(result, Failure):
        return """You are a helpful AI coding assistant. 
Work efficiently, communicate clearly, and help the user accomplish their goals."""

    skill = result.unwrap()
    return f"""# Who I Am
{skill.who_i_am}

# How I Work
{skill.how_i_work}

# How I Communicate
{skill.how_i_communicate}

# My Standards
{skill.my_standards}

# What I Expect From You
{skill.what_i_expect}

# My Reminders to You
{skill.my_reminders}
""".strip()


def regenerate_setup() -> Result[tuple[Skill, dict], str]:
    console.print("[yellow]Regenerating skills and configuration...[/yellow]")

    skills_path = get_skills_path()
    config_path = get_config_path()

    if skills_path.exists():
        try:
            backup_path = skills_path.with_suffix(".md.backup")
            backup_path.write_text(skills_path.read_text())
        except Exception:
            pass

    if config_path.exists():
        try:
            backup_path = config_path.with_suffix(".json.backup")
            backup_path.write_text(config_path.read_text())
        except Exception:
            pass

    return run_onboarding()


def display_current_skill():
    result = load_skills()
    if isinstance(result, Failure):
        console.print(f"[yellow]{result.failure()}[/yellow]")
        console.print("[dim]Run `synlogos --setup` to create your skill.[/dim]")
        return

    skill = result.unwrap()
    console.print()
    console.print(
        Panel(
            Markdown(
                f"""## {skill.name}

### Who I Am
{skill.who_i_am}

### How I Work
{skill.how_i_work}

### How I Communicate
{skill.how_i_communicate}

### My Standards
{skill.my_standards}

### What I Expect From You
{skill.what_i_expect}

### My Reminders to You
{skill.my_reminders}

### Recommended Agents
{", ".join(skill.recommended_agents)}

### Model
{skill.preferred_model}
"""
            ),
            title="[bold green]Current Skill Configuration[/bold green]",
            border_style="green",
        )
    )
    console.print()
