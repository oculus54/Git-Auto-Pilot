# git-auto-shelldm 🤖💻

An intelligent, context-aware command-line assistant that translates natural language into Git commands. Powered by **Qwen 2.5 Coder 32B** and the **Hugging Face Inference API**, it provides a lightning-fast, secure, and interactive shell designed to optimize your Git workflows.

---

## ✨ Key Features

- **🚀 Near-Instant Startup**: Optimized to boot in under 2 seconds (3.7x faster than traditional vector-db CLI tools) by using a lightweight, pure-Python memory system instead of heavy local model engines.
- **📦 Global Installation**: Install with a single command via NPM and run it anywhere in your terminal using the `git-autopilot` command.
- **🔑 Secure Token Onboarding**: Prompts for your Hugging Face API token on first startup and caches it safely in your home directory (`~/.git_autopilot_config.json`) so you don't have to keep pasting it.
- **🛡️ Human-in-the-Loop Safety Gate**: Prompts you for confirmation before executing any generated Git command, protecting your repository from unintended changes.
- **🧠 Global Semantic RAG Memory**: Remembers past successful commands and searches your local cheat sheet. Learning is stored globally in your home directory (`~/.git_autopilot_memory.json`) and shared across all of your local git repositories.
- **🔄 Auto-Correction Loop**: If a command fails to execute, the assistant automatically captures the error output, analyzes it, and attempts to correct and execute it (up to 3 retries).
- **📦 Git LFS Support**: Fully integrated with Git Large File Storage (LFS) commands.

---

## 🚀 Quick Start

### 1. Install Globally
Install the CLI command globally on your system using NPM:
```bash
npm install -g git-auto-shelldm
```
*(Requires Node.js and Python 3 to be installed on your system)*

### 2. Run the Assistant
Launch the interactive shell from within any Git repository:
```bash
git-autopilot
```

### 3. Enter your HF_TOKEN (First run only)
If you do not have the `HF_TOKEN` environment variable set, the assistant will guide you to save it:
```text
Welcome to Git Auto-Pilot!
To use the Hugging Face API, you need a free API token.
Get your token here: https://huggingface.co/settings/tokens
Enter your Hugging Face API Token (HF_TOKEN):
```

---

## 💡 Usage Examples

Type your request in plain English:

```text
Git-Bot> initialize a new repository
Thinking...
Proposed Command: git init
Execute this command? [y/N]: y
```

```text
Git-Bot> track all large ZIP files in the repository
Thinking...
Proposed Command: git lfs track "*.zip"
Execute this command? [y/N]: y
```

---

## 🛠️ How It Works (Architecture)

1. **Lightweight Embedding Retrieval**: Queries the user input embedding using the Hugging Face feature extraction model (`sentence-transformers/all-MiniLM-L6-v2`) and matches it against your global memory database (`~/.git_autopilot_memory.json`) using a pure-Python cosine similarity function.
2. **Context Injection**: Relevant matching commands from the cheat sheet or history are injected into the model's RAG context.
3. **Qwen 2.5 Coder LLM**: The user's query, system path, OS type, and RAG context are sent to `Qwen/Qwen2.5-Coder-32B-Instruct` to output the exact Git command.
4. **Command Execution & Cache**: Upon confirmation, the command is executed. If successful, the input and output are cached locally in the database.
