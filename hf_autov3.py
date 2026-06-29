import os
import csv
import subprocess
import platform
import json
import math
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup Memory and Configuration Files for Global RAG
CONFIG_FILE = os.path.expanduser("~/.git_autopilot_config.json")
MEMORY_FILE = os.path.expanduser("~/.git_autopilot_memory.json")

def get_hf_token():
    token = os.getenv("HF_TOKEN")
    if token:
        return token
        
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                t = data.get("HF_TOKEN")
                if t:
                    return t
        except Exception:
            pass
            
    print("\033[93mWelcome to Git Auto-Pilot!\033[0m")
    print("To use the Hugging Face API, you need a free API token.")
    print("Get your token here: \033[94mhttps://huggingface.co/settings/tokens\033[0m")
    t = input("Enter your Hugging Face API Token (HF_TOKEN): ").strip()
    
    if not t:
        print("\033[91mWARNING: No token entered. Inference requests will fail.\033[0m")
        return ""
        
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"HF_TOKEN": t}, f, indent=4)
        print(f"Token saved successfully to {CONFIG_FILE}\n")
    except Exception as e:
        print(f"Warning: Failed to save token. Error: {e}")
        
    return t

hf_token = get_hf_token()

# We use a powerful open-source coding model.
# Other great options: "meta-llama/Meta-Llama-3-8B-Instruct", "mistralai/Mixtral-8x7B-Instruct-v0.1"
MODEL_ID = "Qwen/Qwen2.5-Coder-32B-Instruct" 
client = InferenceClient(model=MODEL_ID, token=hf_token)

# Setup Memory File for RAG (Git Command History & Cheat Sheet)
# MEMORY_FILE is now defined globally above as a user home path

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"cheat_sheet": [], "history": []}

def save_memory(memory):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory, f, indent=4)
    except Exception as e:
        print(f"Warning: Failed to save memory. Error: {e}")

def flatten_embedding(emb):
    if hasattr(emb, "tolist"):
        emb = emb.tolist()
    while isinstance(emb, list) and len(emb) > 0 and isinstance(emb[0], list):
        emb = emb[0]
    return [float(x) for x in emb]

def cosine_similarity(v1, v2):
    dot = sum(x * y for x, y in zip(v1, v2))
    norm1 = math.sqrt(sum(x * x for x in v1))
    norm2 = math.sqrt(sum(x * x for x in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

def ingest_git_data(memory):
    cheat_sheet_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'git_cheat_sheet.csv')
    if not os.path.exists(cheat_sheet_path):
        return
        
    with open(cheat_sheet_path, mode='r', encoding='utf-8') as file:
        csv_reader = list(csv.DictReader(file))
        
    if len(memory.get("cheat_sheet", [])) == len(csv_reader):
        return

    print("Checking Git Cheat Sheet for RAG ingestion...")
    cheat_sheet_entries = []
    for row in csv_reader:
        task = row['Task']
        command = row['Command']
        
        # Check if we already have this task embedded in memory to avoid calling HF API again
        existing = next((item for item in memory.get("cheat_sheet", []) if item["task"] == task), None)
        if existing:
            cheat_sheet_entries.append(existing)
            continue
            
        print(f"Embedding command: '{command}' for task: '{task}'...")
        try:
            emb = client.feature_extraction(task, model="sentence-transformers/all-MiniLM-L6-v2")
            flat_emb = flatten_embedding(emb)
            cheat_sheet_entries.append({
                "task": task,
                "command": command,
                "embedding": flat_emb
            })
        except Exception as e:
            print(f"Warning: Failed to embed '{task}'. Error: {e}")
            
    memory["cheat_sheet"] = cheat_sheet_entries
    save_memory(memory)
    print("Git data loaded/updated successfully.")

def get_system_context():
    os_name = platform.system()
    cwd = os.getcwd()
    shell_type = "Windows Command Prompt (cmd.exe)" if os.name == 'nt' else "Bash"
    return f"OS: {os_name}, Shell: {shell_type}, CWD: {cwd}"

def generate_command(user_input, context, history_context="", error_message=None, previous_cmd=None):
    system_prompt = f"""You are an expert Git version control assistant. Convert the user request into a valid, up-to-date Git command.

CRITICAL RULES:
1. ONLY output the raw Git command (it should almost always start with 'git ').
2. DO NOT include markdown code blocks (e.g., no ```bash or ```).
3. DO NOT include any explanations or conversational text.
4. Only generate commands related to Git. If the user asks for something unrelated, output 'echo "Error: I only handle Git commands."'
5. If the user request mentions adding or tracking "large files" or "large binaries", prioritize using Git LFS commands (e.g., 'git lfs track "<pattern>"' and 'git lfs install') over standard 'git add'.

System Context:
{context}"""

    user_prompt = ""
    if history_context:
        user_prompt += f"Relevant Past Git Commands (RAG Context):\n{history_context}\n\n"
    if error_message and previous_cmd:
        user_prompt += f"The previous command `{previous_cmd}` failed with this error:\n{error_message}\nCarefully analyze the error and provide a CORRECTED Git command.\n\n"
    
    user_prompt += f"User Request: {user_input}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        response = client.chat_completion(
            messages=messages,
            max_tokens=100,
            temperature=0.1
        )
        cmd = response.choices[0].message.content.strip()
        cmd = cmd.replace("```powershell", "").replace("```bash", "").replace("```sh", "").replace("```", "").strip()
        return cmd
    except Exception as e:
        return f"echo 'Error generating command from Hugging Face: {e}'"

BANNER = (
    "\033[38;5;196m" + r"   _____ _ __                " + "\033[38;5;208m" + r"___         __                " + "\033[38;5;220m" + r"____  _ __     __ " + "\n" +
    "\033[38;5;196m" + r"  / ___/(_) /_     ______   " + "\033[38;5;208m" + r"/   | __  __/ /_____   ______ " + "\033[38;5;220m" + r"/ __ \(_) /___ / /_" + "\n" +
    "\033[38;5;196m" + r" / / __/ / __/    /_____/  " + "\033[38;5;208m" + r"/ /| |/ / / / __/ __ \ /_____/" + "\033[38;5;220m" + r"/ /_/ / / / __ \/ __/" + "\n" +
    "\033[38;5;196m" + r"/ /_/ / / /_              " + "\033[38;5;208m" + r"/ ___ / /_/ / /_/ /_/ /       " + "\033[38;5;220m" + r"/ ____/ / / /_/ / /_  " + "\n" +
    "\033[38;5;196m" + r"\____/_/\__/             " + "\033[38;5;208m" + r"/_/  |_\__,_/\__/\____/       " + "\033[38;5;220m" + r"/_/   /_/_/\____/\__/  " + "\033[0m\n"
)

def ai_shell():
    memory = load_memory()
    ingest_git_data(memory)
    print(BANNER)
    print(f"Git AI Assistant Initialized (Powered by {MODEL_ID.split('/')[-1]}). Type 'exit' to quit.")
    
    while True:
        user_input = input("\nGit-Bot> ")
        if user_input.lower() in ['exit', 'quit']: break
        if not user_input.strip(): continue
        
        # 1. Retrieve RAG Context
        history_context = ""
        try:
            emb = client.feature_extraction(user_input, model="sentence-transformers/all-MiniLM-L6-v2")
            query_emb = flatten_embedding(emb)
            
            candidates = memory.get("cheat_sheet", []) + memory.get("history", [])
            if candidates:
                scored = []
                for item in candidates:
                    sim = cosine_similarity(query_emb, item["embedding"])
                    scored.append((sim, item))
                # Sort by similarity descending
                scored.sort(key=lambda x: x[0], reverse=True)
                
                # Retrieve top 3 matches with similarity > 0.25
                top_matches = [item for sim, item in scored[:3] if sim > 0.25]
                if top_matches:
                    history_context = "\n".join(
                        [f"- Request: '{item['task']}', Command: '{item['command']}'"
                         for item in top_matches]
                    )
        except Exception as e:
            print(f"Warning: Failed to retrieve RAG context. Error: {e}")
        
        context = get_system_context()
        error_msg = None
        current_cmd = None
        max_retries = 3
        retry_count = 0
        
        # 2. Agentic Loop
        while retry_count < max_retries:
            print(f"Thinking...", end="\r")
            cmd = generate_command(user_input, context, history_context, error_msg, current_cmd)
            current_cmd = cmd
            
            # --- SAFETY GATE ADDED HERE ---
            print(f"\nProposed Command: \033[92m{cmd}\033[0m")
            confirm = input("Execute this command? [y/N]: ")
            if confirm.lower() != 'y':
                print("Execution cancelled by user.")
                break
            # ------------------------------

            print(f"Executing: {cmd}")
            process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if process.stdout: print(process.stdout)
            
            # 3. Success -> Store to Memory
            if process.returncode == 0:
                try:
                    # Avoid duplicates in history
                    if not any(item["task"] == user_input and item["command"] == cmd for item in memory.get("history", [])):
                        emb = client.feature_extraction(user_input, model="sentence-transformers/all-MiniLM-L6-v2")
                        flat_emb = flatten_embedding(emb)
                        memory.setdefault("history", []).append({
                            "task": user_input,
                            "command": cmd,
                            "embedding": flat_emb
                        })
                        save_memory(memory)
                except Exception as e:
                    pass 
                break
            # 4. Failure -> Retry Loop
            else:
                print(f"\033[91mExecution Failed (Exit Code: {process.returncode}):\033[0m")
                if process.stderr: print(process.stderr)
                error_msg = process.stderr or "Unknown Error"
                print("Attempting auto-correction...")
                retry_count += 1
                
        if retry_count >= max_retries:
            print("Max auto-correction retries reached. Cancelling.")

if __name__ == "__main__":
    ai_shell()
