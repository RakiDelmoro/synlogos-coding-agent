# Synlogos

> In the beginning was the Code, and the Code was with the AI, and the Code was AI.

A professional AI coding agent built with functional programming patterns in Python. Synlogos acts as your autonomous coding companion, capable of reading, writing, editing files, executing shell commands, running code, and managing git operations.

![Synlogos CLI](cli-display.png)

## Features

- **Autonomous Coding Agent** — Interact naturally to accomplish complex coding tasks
- **TogetherAI Powered** — Uses Llama-3.3-70B-Instruct-Turbo with 128K context
- **Functional Architecture** — Built with Result monads, immutable state, and pure functions
- **Rich Tool Set**:
  - File operations: read, write, edit
  - Shell command execution
  - Code execution in sandboxed environment
  - File search: glob patterns, grep/regex search
  - Git integration: status, diff, log, commit
- **Beautiful CLI** — Rich terminal output with markdown rendering
- **Safe Execution** — Local sandbox for isolated code execution

## Installation

```bash
# Clone the repository
git clone https://github.com/RakiDelmoro/synlogos-coding-agent.git
cd synlogos-coding-agent

# Install with pip
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

## Quick Start

1. Set your TogetherAI API key:

```bash
export TOGETHER_API_KEY="your-api-key-here"
```

Get your API key at [TogetherAI](https://api.together.xyz/settings/api-keys).

2. Run Synlogos:

```bash
synlogos
```

Or directly:

```bash
python -m src.cli
```

## Usage

Once started, you'll see an interactive prompt. Just describe what you want to do:

```
You: Create a Python function that calculates fibonacci numbers and write it to fib.py

You: Read all the TypeScript files in src/ and summarize their purpose

You: Run the tests and fix any failing tests

You: Commit the changes with a descriptive message
```

Type `exit` or `quit` to end the session.

## Architecture

Synlogos is built with functional programming principles:

- **Result Monads** — Explicit error handling using the `returns` library
- **Immutable State** — State is threaded through pure functions, never mutated
- **Factory Functions** — Tools and agents created via `create_tool()`, `create_agent()` patterns
- **Protocol-based Design** — Clean interfaces for extensibility

```
src/
├── agent/           # Agent implementations
│   └── synlogos.py  # Main Synlogos agent
├── providers/       # LLM providers (TogetherAI)
├── sandbox/         # Code execution sandbox
├── tools/           # Tool implementations
│   ├── files.py     # File operations
│   ├── shell.py     # Shell commands
│   ├── code.py      # Code execution
│   └── git_tools.py # Git operations
├── types.py         # Type definitions
├── protocols.py     # Protocol interfaces
└── cli.py           # CLI entry point
```

## Configuration

Synlogos uses `AgentConfig` for configuration:

```python
from src.types import AgentConfig

config = AgentConfig(
    model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
    max_turns=30
)
```

## Requirements

- Python 3.11+
- TogetherAI API key
- Docker (optional, for sandboxed code execution)

## Dependencies

- `together` — TogetherAI SDK
- `pydantic` — Data validation
- `returns` — Result monads for functional error handling
- `rich` — Beautiful terminal output
- `aiofiles` — Async file operations
- `httpx` — HTTP client

## Development

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

## License

MIT License — see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

Built with love using:
- [TogetherAI](https://together.ai) — Fast, affordable LLM inference
- [Rich](https://github.com/Textualize/rich) — Beautiful terminal formatting
- [Returns](https://github.com/dry-python/returns) — Functional programming in Python
