# AutoShell 🤖💻

An intelligent, context-aware command-line assistant that translates natural language into functional OS commands. Powered by LLMs (Google Gemini & Hugging Face), AutoShell not only generates commands but learns from your environment and past successes to improve accuracy over time.

## ✨ Project Evolution & Features

This repository contains multiple iterations of the AutoShell assistant, demonstrating progressive enhancements in functionality, focus, and safety:

### 1. General OS Assistant (`prototype.py`)
- **Natural Language to OS Commands**: Translates plain English into Windows (cmd.exe) or Linux/Mac (Bash) commands.
- **Context-Aware Generation**: Automatically detects your Operating System and Current Working Directory (CWD).
- **Retrieval-Augmented Generation (RAG)**: Uses **ChromaDB** as a local vector database to store command history. Learns from past successful requests to ensure high accuracy.
- **Agentic Auto-Correction Loop**: Executes commands, captures error messages (`stderr`) on failure, and autonomously attempts to self-correct the command (up to 3 retries).
- **Model**: Powered by the Google Gemini 2.5 Flash API.

### 2. Git-Specific Assistant (`ver1forgit.py`)
- **Git Expert**: Strict focus on generating valid, up-to-date Git version control commands. Refuses non-Git tasks.
- **Knowledge Base Ingestion**: Pre-loads a local `git_cheat_sheet.csv` into ChromaDB for initial RAG context before you even type your first prompt.
- **Agentic Loop**: Retains the self-correction mechanism for failed Git commands.
- **Model**: Powered by the Google Gemini 2.5 Flash API.

### 3. Open-Source LLMs & Safety Gate (`hf_autoshell.py`)
- **Hugging Face Integration**: Powered by the Hugging Face Inference API (defaults to `Qwen/Qwen2.5-Coder-32B-Instruct`), allowing flexibility to swap to models like Llama 3 or Mixtral.
- **Human-in-the-Loop Safety Gate**: Introduces a critical confirmation prompt (`[y/N]`) before executing any proposed command, preventing destructive actions.
- **Robust RAG Updates**: Uses `upsert` for ChromaDB insertions to prevent database crashes when reloading the Git cheat sheet or duplicate history.

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   pip install google-generativeai chromadb huggingface_hub python-dotenv
   ```
2. **Setup your Environment:**
   Create a `.env` file in the root directory and add your API keys:
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   HF_TOKEN=your_huggingface_token
   ```
3. **Run the desired assistant:**
   - For the General Shell (Gemini): `python prototype.py`
   - For the Git Shell (Gemini): `python ver1forgit.py`
   - For the Git Shell (Hugging Face with Safety Gate): `python hf_autoshell.py`

## 🛠️ How the Agentic Architecture Works

When you enter a prompt (e.g., `undo my last commit`):
1. **Query RAG**: Searches ChromaDB for similar past tasks or relevant cheat sheet entries.
2. **Context Compilation**: Gathers OS details, CWD, RAG results, and your specific prompt.
3. **LLM Generation**: Requests the exact, markdown-stripped command from the configured LLM.
4. **Safety Check** *(in `hf_autoshell.py`)*: Presents the command to you in the terminal and waits for confirmation.
5. **Execution & Self-Correction**: 
   - **On Success** -> Automatically saves the interaction (Prompt + Command) to ChromaDB memory.
   - **On Failure** -> Captures the raw OS error, feeds it back to the LLM, and retries the loop (up to 3 times).
