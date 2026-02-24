# Synlogos

**Local AI coding assistant that just works.**

Synlogos turns your local Ollama models into a powerful coding assistant. No configs, no cloud, no complexity. Install, run, code.

![Synlogos CLI](cli-display.png)

## ⚡ Quick Start (2 minutes)

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull a model
ollama pull qwen3:8b

# 3. Install Synlogos
git clone https://github.com/RakiDelmoro/synlogos-coding-agent.git
cd synlogos-coding-agent
pip install -e .

# 4. Run it
synlogos
```

That's it. No setup, no config files, no API keys.

## 🎯 What is Synlogos?

A coding assistant that:
- ✅ Runs 100% locally on your machine (via Ollama)
- ✅ Needs zero configuration
- ✅ Understands your codebase
- ✅ Writes, edits, and refactors code
- ✅ Runs tests and fixes bugs
- ✅ Searches and explores files
- ✅ Works offline

## 🚀 Usage

Just run `synlogos` and start chatting:

```bash
$ synlogos

You: Create a Python function that reverses a string
You: Find all files that import requests
You: Run the tests and tell me what's failing
You: Refactor this class to use dataclasses
```

**Slash commands** while running:
- `/help` - Show all commands
- `/agents` - List available agent types
- `/exit` - Quit

**Agent types** (for specific tasks):
```bash
synlogos --agent explore    # Fast file exploration
synlogos --agent code      # Complex coding tasks
synlogos --agent test      # Testing focus
synlogos --agent review    # Code review
```

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

1. **Auto-detect** — Finds Ollama running on localhost:11434
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
