# Synlogos

**Local AI coding assistant that just works.**

Synlogos turns your local Ollama models into a powerful coding assistant. No configs, no cloud, no complexity. Install, run, code.

![Synlogos CLI](cli-display.png)

## ⚡ Quick Start (2 minutes)

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Start Ollama
ollama serve

# 3. Install Synlogos
git clone https://github.com/RakiDelmoro/synlogos-coding-agent.git
cd synlogos-coding-agent
pip install -e .

# 4. Run setup (selects/installs your model)
synlogos --setup

# 5. Start coding!
synlogos
```

**Setup command** (`synlogos --setup`) will:
- Detect available Ollama models
- Let you choose which model to use
- Automatically pull the model if not installed
- Configure Synlogos to use it

That's it. No manual config files, no API keys.

## 🐳 Docker Support

Running Ollama in a separate Docker container? No problem!

```bash
# Set the Ollama host (e.g., if Ollama is in another container named 'ollama')
export OLLAMA_HOST=ollama:11434

# Or use IP address
export OLLAMA_HOST=192.168.1.100:11434

# Then run synlogos
synlogos
```

The `OLLAMA_HOST` environment variable tells Synlogos where to find your Ollama instance. Default is `localhost:11434`.

**Example with Docker Compose:**

```yaml
version: '3.8'
services:
  ollama:
    image: ollama/ollama
    volumes:
      - ollama:/root/.ollama
    
  synlogos:
    build: .
    environment:
      - OLLAMA_HOST=ollama:11434
    volumes:
      - .:/workspace
    working_dir: /workspace
    depends_on:
      - ollama
```

## 🎯 What is Synlogos?

A coding assistant that:
- ✅ Runs 100% locally on your machine (via Ollama)
- ✅ Needs zero configuration
- ✅ Understands your codebase
- ✅ Writes, edits, and refactors code
- ✅ Runs tests and fixes bugs
- ✅ Searches and explores files
- ✅ Works offline
- ✅ Supports remote Ollama instances

## 🚀 Usage

**First time?** Run setup to select your model:
```bash
synlogos --setup
```

Then just run `synlogos` and start chatting:

```bash
$ synlogos

You: Create a Python function that reverses a string
You: Find all files that import requests
You: Run the tests and tell me what's failing
You: Refactor this class to use dataclasses
```

**CLI commands:**
- `synlogos --setup` - Select/change model
- `synlogos --agent explore` - Use specific agent
- `synlogos --check-ollama` - Check Ollama status

**Slash commands** while running:
- `/help` - Show all commands
- `/agents` - List available agent types
- `/exit` - Quit

## 🛠️ Tools Available

Your AI can:
- **Read/write/edit** files
- **Run shell** commands
- **Search** with glob patterns and grep
- **Execute** Python code safely
- **Git** operations (status, diff, commit)

## 📦 Requirements

- Python 3.11+
- Ollama (auto-detected, auto-configured)

## 🧩 How It Works

1. **Auto-detect** — Finds Ollama at `OLLAMA_HOST` (default: localhost:11434)
2. **Auto-config** — Creates optimal settings for your model
3. **Smart routing** — Simple tasks use direct tools, complex tasks get full code generation
4. **Auto-compact** — Summarizes long conversations automatically

No `synlogos.json` to edit. No `skills.md` to write. It just works.

## 🏃 Available Models

| Model | Speed | Quality | Best For |
|-------|-------|---------|----------|
| `qwen3:8b` | ⚡ Fast | ⭐⭐⭐ Good | General coding (recommended) |
| `qwen3:14b` | 🐢 Medium | ⭐⭐⭐⭐ Better | Complex tasks |
| `deepseek-coder:6.7b` | ⚡ Fast | ⭐⭐⭐⭐ Good | Code-focused |
| `llama3.1:8b` | ⚡ Fast | ⭐⭐⭐ Good | Alternative option |

**Pull any model:**
```bash
ollama pull qwen3:8b
ollama pull deepseek-coder:6.7b
```

## 🔒 Privacy

- **100% local** — No internet required after model download
- **No data sharing** — Your code never leaves your machine
- **No tracking** — Zero telemetry or analytics
- **No accounts** — No signup, no API keys
- **Flexible hosting** — Run Ollama locally or on another machine/container

## 🎮 Example Session

```bash
$ synlogos
✓ Connected to Ollama (qwen3:8b)

You: Create a Fibonacci function
Assistant: [writes fib.py with function]

You: Now add a main block that prints first 10 numbers
Assistant: [edits file]

You: Run it
Assistant: [runs python fib.py]
0, 1, 1, 2, 3, 5, 8, 13, 21, 34

You: /exit
```

## 🔧 Troubleshooting

**Ollama not running?**
```bash
ollama serve
```

**Ollama in Docker/container?**
```bash
export OLLAMA_HOST=your-ollama-host:11434
synlogos
```

**Model not found?**
```bash
ollama pull qwen3:8b
```

**Check status:**
```bash
synlogos --check-ollama
```

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.

---

**Install. Run. Code.** No config, no cloud, no complexity.
