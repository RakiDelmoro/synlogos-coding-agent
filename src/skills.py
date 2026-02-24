"""Skills management for Synlogos - AI-powered persona generation using TinySkills technique"""

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

# Opencode agent style template
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

# Available models
AVAILABLE_MODELS = {
    1: ("togetherai/moonshotai/Kimi-K2.5", "TogetherAI Kimi-K2.5 (Powerful, paid)"),
    2: ("opencode/glm-5-free", "OpenCode GLM-5 Free (Free tier)"),
    3: ("opencode/kimi-k2-free", "OpenCode Kimi-K2 Free (Free tier)"),
    4: ("ollama/qwen3:8b", "Ollama Qwen3 8B (Local, requires Ollama)"),
}

# Agent type definitions
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
        "model": "togetherai/moonshotai/Kimi-K2.5",
        "instructions": "You are a planning agent. Deeply analyze the task and codebase context provided, identify edge cases, dependencies, and risks, then produce a clear ordered step-by-step plan before any code is written.",
    },
    "code": {
        "description": "Primary coding agent",
        "lightweight": False,
        "model": "togetherai/moonshotai/Kimi-K2.5",
        "instructions": "You are the primary coding agent. Write, edit, refactor, and debug code with high accuracy. Handle complex multi-file changes, architecture decisions, and difficult bugs.",
    },
    "architect": {
        "description": "Senior software architect",
        "lightweight": False,
        "model": "togetherai/moonshotai/Kimi-K2.5",
        "instructions": "You are a senior software architect. Design systems, plan large refactors, choose technologies, and reason about scalability and maintainability.",
    },
    "web_search": {
        "description": "Web search specialist",
        "lightweight": False,
        "model": "togetherai/moonshotai/Kimi-K2.5",
        "instructions": "You are a web search specialist. Retrieve accurate, up-to-date information from the web. Summarize results concisely, cite sources, and handle ambiguity carefully.",
    },
    "memory": {
        "description": "Memory management agent",
        "lightweight": False,
        "model": "togetherai/moonshotai/Kimi-K2.5",
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
        "model": "togetherai/moonshotai/Kimi-K2.5",
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
    preferred_model: str = "togetherai/moonshotai/Kimi-K2.5"


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


def select_model() -> str:
    console.print()
    console.print("[bold cyan]Select your preferred model:[/bold cyan]")
    console.print()

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="cyan", width=4)
    table.add_column("Model", style="green")
    table.add_column("Description", style="dim")

    for num, (model_id, description) in AVAILABLE_MODELS.items():
        table.add_row(str(num), model_id, description)

    console.print(table)
    console.print()

    choice = IntPrompt.ask(
        "[bold blue]Enter model number[/bold blue]",
        default=1,
        show_default=True,
    )

    if choice in AVAILABLE_MODELS:
        return AVAILABLE_MODELS[choice][0]
    else:
        console.print("[yellow]Invalid choice, using default model[/yellow]")
        return "togetherai/moonshotai/Kimi-K2.5"


def get_api_key_for_model(model: str) -> str | None:
    if model.startswith("togetherai"):
        return os.environ.get("TOGETHER_API_KEY", "")
    elif model.startswith("opencode"):
        return os.environ.get("OPENCODE_API_KEY", "")
    return None


class TinySkillsGenerator:
    """Generate comprehensive skill using multi-question TinySkills technique"""

    def __init__(self, model: str, api_key: str | None):
        self.model = model
        self.api_key = api_key or get_api_key_for_model(model)
        self.responses = {}

    def _get_client(self):
        """Get OpenAI client for the selected provider"""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed")

        parts = self.model.split("/")
        provider = parts[0] if len(parts) >= 1 else "togetherai"

        if provider == "togetherai":
            base_url = "https://api.together.xyz/v1"
            api_key = self.api_key or os.environ.get("TOGETHER_API_KEY", "")
            model_name = (
                "/".join(parts[1:]) if len(parts) > 1 else "meta-llama/Llama-3.3-70B-Instruct"
            )
        elif provider == "opencode":
            base_url = "https://opencode.ai/zen/v1"
            api_key = self.api_key or os.environ.get("OPENCODE_API_KEY", "")
            model_name = parts[1] if len(parts) > 1 else "glm-5-free"
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        if not api_key:
            raise ValueError(f"No API key for {provider}")

        return OpenAI(base_url=base_url, api_key=api_key), model_name

    def _ask_question(self, question: str, context: str = "") -> str:
        """Ask a single question to the LLM"""
        client, model_name = self._get_client()

        system_prompt = """You are a persona designer for an AI coding assistant.
Answer the question thoughtfully and concisely (2-4 sentences).
Be specific, actionable, and authentic to the persona being created.
Focus on practical behaviors, not generic advice."""

        user_prompt = f"{context}\n\nQuestion: {question}\n\nAnswer concisely in 2-4 sentences:"

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=300,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            console.print(f"[dim red]LLM call failed: {e}[/dim red]")
            return ""

    def generate_persona(self, user_description: str) -> dict[str, str]:
        """Generate comprehensive persona using multiple targeted questions"""

        console.print()
        console.print("[dim]Generating your personalized AI assistant...[/dim]")
        console.print()

        context = f'Creating an AI coding assistant persona based on: "{user_description}"'

        # Phase 1: Core Identity Questions (like TinySkills' multi-source approach)
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
            console.print(f"  [dim green]✓[/dim green] [dim]{key} captured[/dim]")

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
            console.print(f"  [dim green]✓[/dim green] [dim]{key} captured[/dim]")

        # Phase 3: Principles & Reminders
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
            console.print(f"  [dim green]✓[/dim green] [dim]{key} captured[/dim]")

        # Synthesize final persona
        console.print()
        console.print("[dim cyan]Synthesizing complete persona...[/dim cyan]")

        return {
            "who_i_am": self.responses.get("identity", ""),
            "how_i_work": self.responses.get("approach", ""),
            "how_i_communicate": self.responses.get("style", ""),
            "my_standards": self.responses.get("standards", ""),
            "what_i_expect": self.responses.get("expectations", ""),
            "my_reminders": self.responses.get("reminders", ""),
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


def generate_skill_with_tinyskills(
    user_description: str, model: str, api_key: str | None
) -> Result[Skill, str]:
    """Generate skill using TinySkills multi-question technique"""

    try:
        generator = TinySkillsGenerator(model, api_key)
        persona_data = generator.generate_persona(user_description)

        # Check if we got meaningful responses
        if not any(persona_data.values()):
            return Failure("LLM generation produced empty results")

        # Generate skill name from description
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

    except ImportError as e:
        return Failure(f"Missing dependency: {e}")
    except ValueError as e:
        return Failure(f"Configuration error: {e}")
    except Exception as e:
        return Failure(f"Generation failed: {e}")


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
    """Generate synlogos.json config"""
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
            "model": "togetherai/moonshotai/Kimi-K2.5",
            "instructions": AGENT_TYPES["memory"]["instructions"],
        }

    return {
        "$schema": "https://opencode.ai/config.json",
        "theme": "matrix",
        "instructions": ["skills.md"],
        "provider": {
            "opencode": {
                "npm": "@ai-sdk/openai-compatible",
                "options": {
                    "baseURL": "https://opencode.ai/zen/v1",
                    "apiKey": "",
                },
                "models": {
                    "glm-5-free": {"model": "glm-5-free"},
                    "glm-5": {"model": "glm-5"},
                    "kimi-k2-free": {"model": "kimi-k2-free"},
                },
            },
            "ollama": {
                "npm": "@ai-sdk/openai-compatible",
                "options": {"baseURL": "http://ollama:11434/v1"},
                "models": {"qwen3:8b": {"model": "qwen3:8b"}},
            },
            "togetherai": {
                "npm": "@ai-sdk/openai-compatible",
                "options": {
                    "baseURL": "https://api.together.xyz/v1",
                    "apiKey": "",
                },
                "models": {"moonshotai/Kimi-K2.5": {}},
            },
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
    """Run onboarding to create personalized AI assistant"""
    console.print()
    console.print(
        Panel.fit(
            "[bold green]Welcome to Synlogos![/bold green]\n"
            "Let's create your personalized AI coding assistant.",
            border_style="green",
        )
    )
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

    # Select model
    selected_model = select_model()
    api_key = get_api_key_for_model(selected_model)

    if not api_key and selected_model.startswith(("togetherai", "opencode")):
        console.print()
        console.print(
            f"[yellow]Warning: No API key found for {selected_model.split('/')[0]}.[/yellow]"
        )
        console.print(
            f"[dim]Set {selected_model.split('/')[0].upper()}_API_KEY for best results.[/dim]"
        )
        console.print()

    # Generate skill using TinySkills
    result = generate_skill_with_tinyskills(user_description, selected_model, api_key)

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
