# ShellAI 🤖💻

An intelligent, context-aware command-line assistant that translates natural language into functional OS commands. Powered by the Gemini 2.5 Flash API, ShellAI not only generates commands but learns from your environment and past successes to improve accuracy over time.

## ✨ Features Built So Far

1. **Natural Language to OS Commands**: Type what you want to do in plain English, and ShellAI translates it into the appropriate command for your OS.
2. **Context-Aware Generation**: Automatically detects your Operating System and Current Working Directory (CWD) to provide accurate pathing and OS-specific syntax.
3. **Retrieval-Augmented Generation (RAG)**: 
    - Uses **ChromaDB** as a local vector database to store your command history.
    - When you ask for a command, ShellAI retrieves similar past successful requests to learn your preferences and ensure high accuracy.
4. **Agentic Auto-Correction Loop**: 
    - Automatically executes the command.
    - If a command fails (non-zero exit code), ShellAI captures the error message (`stderr`), feeds it back to the AI, and autonomously attempts to generate and run a corrected command (up to 3 retries).
5. **Markdown & Hallucination Safety Nets**: Enforces strict system prompting and post-processing to strip out markdown formatting, ensuring scripts don't crash the execution loop.
6. **Secure Configuration**: Uses environment variables (`GEMINI_API_KEY`) to keep your API keys secure.

## 🚀 Quick Start

1. Install dependencies:
   ```bash
   pip install google-generativeai chromadb
   ```
2. Set your API Key:
   - **Windows (cmd)**: `set GEMINI_API_KEY="your_api_key"`
   - **Linux/Mac**: `export GEMINI_API_KEY="your_api_key"`
3. Run the shell:
   ```bash
   python 1.py
   ```

## 🛠️ How it Works
When you enter a prompt (e.g., `open notepad`), ShellAI:
1. Queries ChromaDB for similar past tasks.
2. Compiles your OS context, past similar tasks, and your prompt.
3. Asks Gemini for the exact command.
4. Executes it immediately.
5. If it fails, it enters a self-correction loop until it succeeds or hits the retry limit.
6. If it succeeds, it saves the interaction to its memory (RAG) for future reference.
