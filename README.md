# Synlogos

**Local AI coding assistant powered by Ollama**

Synlogos is a privacy-focused, local AI coding agent that runs entirely on your machine. No cloud providers, no API keys, no data leaving your computer. Just you, your code, and your locally-running AI models.

![Synlogos CLI](cli-display.png)

## 🌟 Key Features

- **100% Local** — All AI models run locally via Ollama. Your code never leaves your machine.
- **Privacy-First** — No cloud dependencies, no API keys, no tracking. Complete data sovereignty.
- **Personalized AI** — Creates a custom skill/persona based on your preferences using multi-phase AI questioning
- **Specialized Agents** — Different agents optimized for specific tasks:
  - `explore` — Fast file and codebase exploration
  - `code` — Primary coding agent for complex tasks
  - `architect` — System design and architecture decisions
  - `plan` — Task planning and analysis
  - `test` — Testing specialist
  - `review` — Code review agent
  - `docs` — Documentation writer
- **Smart Agent Selection** — Automatically selects appropriate agents based on your needs
- **Hybrid Tool Calling** — Intelligent routing between direct tools and programmatic orchestration
- **Auto-Compact** — Automatically summarizes conversation at 80% of context limit
- **Session Metrics** — Real-time tracking of tool usage and efficiency
- **Beautiful CLI** — Rich terminal output with markdown rendering

## 🚀 Quick Start

### Prerequisites

1. **Install Ollama**
   ```bash
   # macOS/Linux
   curl -fsSL https://ollama.com/install.sh | sh
   
   # Or download from https://ollama.com
   ```

2. **Start Ollama**
   ```bash
   ollama serve
   ```

3. **Pull a model** (start with qwen3:8b for best balance)
   ```bash
   ollama pull qwen3:8b
   ```

### Installation

```bash
# Clone the repository
git clone https://github.com/RakiDelmoro/synlogos-coding-agent.git
cd synlogos-coding-agent

# Install
pip install -e .
```

### First Run

```bash
# Run setup to create your personalized AI assistant
synlogos --setup
```

This will:
1. Ask what you want your AI assistant to be (mentor, fast coder, reviewer, etc.)
2. Let you choose from available Ollama models
3. Generate a personalized `skills.md` (your AI's persona)
4. Create `synlogos.json` with optimized agent configuration

### Usage

```bash
# Start your AI assistant
synlogos

# Use a specific agent type
synlogos --agent explore
synlogos --agent code
synlogos --agent architect

# Check Ollama status
synlogos --check-ollama

# View your current skill
synlogos --skill

# Regenerate your skill/persona
synlogos --reskill
```

## 💬 Interactive Usage

Once started, you'll see an interactive prompt:

```
You: Create a Python function that calculates fibonacci numbers

You: Read all the TypeScript files in src/ and summarize their purpose

You: Review this code for potential bugs

You: Help me refactor this class into smaller functions
```

Type `exit` or `quit` to end the session.

### Slash Commands

While the agent is running, use slash commands:

```
/help              Show available slash commands
/agents            List all available agent types
/provider          Show current model
/providers         Check Ollama status and available models
/tokens            Show current token usage
/metrics           Show session tool usage metrics
/config            Show current configuration
clear              Clear the screen
/exit              Exit the session
```

## 🎯 How It Works

### TinySkills Persona Generation

Synlogos uses a **multi-phase questioning technique** (inspired by TinySkills) to generate your personalized AI assistant:

**Phase 1: Core Identity** (3 questions)
- "Who are you?" → Defines identity and personality
- "How do you approach tasks?" → Establishes methodology
- "How do you communicate?" → Sets tone and style

**Phase 2: Standards & Expectations** (2 questions)
- "What are your coding standards?"
- "What do you expect from the user?"

**Phase 3: Principles** (1 question)
- "What are your key principles?"

This creates a rich `skills.md` file that defines your AI's persona.

### Smart Agent Selection

Based on your description, Synlogos automatically selects appropriate agents:

| If you want... | You get these agents |
|----------------|---------------------|
| A mentor/teacher | explore, code, architect, **docs** |
| Fast prototyping | explore, code, **test**, **grep** |
| Code review | **review**, **security**, **test**, **grep** |
| Pair programming | explore, **plan**, **architect**, code |
| Documentation | **docs**, **summarize**, explore |
| Testing/debug | **test**, explore, **review**, code |

### Available Models

| Model | Best For |
|-------|----------|
| `qwen3:8b` | Fast, good for most tasks (default) |
| `qwen3:14b` | Better quality, slower |
| `qwen3:32b` | Best quality, slowest |
| `llama3.1:8b` | Alternative option |
| `deepseek-coder:6.7b` | Coding focused |
| `deepseek-coder:33b` | Best for complex coding |

### Hybrid Tool Calling

Synlogos intelligently chooses between:

**Direct Tools** — Simple operations (43% fewer tokens)
- `read_file`, `write_file`, `edit_file`
- `shell` commands
- `glob`, `grep` search

**Orchestration** — Complex multi-step tasks
- Write Python code that calls multiple tools
- Parallel execution via `asyncio.gather()`
- Batch operations and complex logic

## 🛠️ Configuration

Synlogos creates `synlogos.json` automatically during setup. Example:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "theme": "matrix",
  "instructions": ["skills.md"],
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "options": {
        "baseURL": "http://localhost:11434/v1"
      },
      "models": {
        "qwen3:8b": {"model": "qwen3:8b"},
        "qwen3:14b": {"model": "qwen3:14b"},
        "deepseek-coder:33b": {"model": "deepseek-coder:33b"}
      }
    }
  },
  "model": "ollama/qwen3:8b",
  "agent": {
    "explore": {
      "model": "ollama/qwen3:8b",
      "instructions": "You are a fast file and codebase explorer..."
    },
    "code": {
      "model": "ollama/deepseek-coder:33b",
      "instructions": "You are the primary coding agent..."
    }
  }
}
```

### skills.md Example

Your personalized AI persona:

```markdown
# A senior engineer who mentors me through complex refactors

## Who I Am
I am your mentor and teacher. I don't just solve problems—I help you understand them...

## How I Work
I start by understanding your current knowledge level. I break complex problems into digestible pieces...

## How I Communicate
I communicate clearly and patiently. I use analogies and examples...

## My Standards
I value understanding over speed. I won't just hand you code...

## What I Expect From You
Tell me what you've already tried. Ask 'why' when you don't understand...

## My Reminders to You
Every senior engineer was once completely lost. If you can't explain it simply, you don't understand it yet...
```

## 📁 Project Structure

```
src/
├── agent/              # Agent implementations
│   └── synlogos.py     # Main Synlogos agent
├── providers/          # LLM providers (Ollama-only)
│   └── unified_provider.py
├── skills.py           # Skill/persona generation
├── sandbox/            # Code execution sandbox
├── tools/              # Tool implementations
│   ├── functional_tools.py
│   ├── advanced_tools.py
│   └── git_tools.py
├── config.py           # Configuration loader
├── types.py            # Type definitions
└── cli.py              # CLI entry point
```

## 📊 Session Metrics

Track your session efficiency:

```
============================================================
SESSION METRICS
============================================================
Session duration: 0:05:23
Total prompts: 12
Direct tool calls: 15
Orchestration calls: 3

Tool Usage Breakdown:
------------------------------------------------------------
  write_file             5 calls  100.0% success
  read_file              8 calls  100.0% success
  orchestrate            3 calls  100.0% success
------------------------------------------------------------
Hybrid ratio: 15:3 (direct:orchestrate)
============================================================
```

## 🔄 Recent Updates

### Ollama-Only Edition
- Removed all cloud providers (TogetherAI, OpenCode, Groq)
- Added TinySkills multi-phase persona generation
- Automatic model pulling during setup
- Enhanced Ollama status checking
- Privacy-first: 100% local execution

### v2.0 Features
- Hybrid tool calling with intelligent routing
- Auto-compact conversation management
- Session metrics tracking
- Multi-agent support with specialized roles
- Rich CLI with beautiful formatting

## ⚙️ Requirements

- Python 3.11+
- Ollama installed and running
- (Optional) Docker for enhanced sandboxing

## 📦 Dependencies

- `openai` — OpenAI-compatible SDK for Ollama
- `pydantic` — Data validation
- `returns` — Result monads for functional error handling
- `rich` — Beautiful terminal output
- `aiofiles` — Async file operations

## 🧪 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run linting
ruff check .

# Run type checking
mypy src/

# Run tests
pytest
```

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

Built with:
- [Ollama](https://ollama.ai) — Local LLM inference
- [Rich](https://github.com/Textualize/rich) — Beautiful terminal formatting
- [Returns](https://github.com/dry-python/returns) — Functional programming in Python
- Inspired by [TinySkills](https://github.com/tinyfish-io/tinyfish-cookbook/tree/main/tinyskills) — Multi-source synthesis technique

---

**Your code. Your models. Your privacy.**
