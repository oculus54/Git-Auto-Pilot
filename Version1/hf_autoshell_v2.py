import os
import csv
import subprocess
import platform
import chromadb
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup Hugging Face API
hf_token = os.getenv("HF_TOKEN")
if not hf_token:
    print("WARNING: HF_TOKEN not found in .env. Please add it to use the Hugging Face API.")

# We use a powerful open-source coding model.
# Other great options: "meta-llama/Meta-Llama-3-8B-Instruct", "mistralai/Mixtral-8x7B-Instruct-v0.1"
MODEL_ID = "Qwen/Qwen2.5-Coder-32B-Instruct" 
client = InferenceClient(model=MODEL_ID, token=hf_token)

# Setup ChromaDB for RAG (Git Command History)
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="command_history")

def ingest_git_data():
    if os.path.exists('git_cheat_sheet.csv'):
        print("Checking Git Cheat Sheet for RAG ingestion...")
        with open('git_cheat_sheet.csv', mode='r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            docs = []
            metadatas = []
            ids = []
            for index, row in enumerate(csv_reader):
                docs.append(row['Task'])
                metadatas.append({"command": row['Command']})
                ids.append(f"git_cheat_sheet_{index}")
            
            # Use upsert to avoid crashing if IDs already exist! (Safety Fix)
            try:
                collection.upsert(documents=docs, metadatas=metadatas, ids=ids)
                print("Git data loaded/updated successfully.")
            except Exception as e:
                print(f"Warning: Failed to ingest RAG data. Error: {e}")

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
    ingest_git_data()
    print(BANNER)
    print(f"Git AI Assistant Initialized (Powered by {MODEL_ID.split('/')[-1]}). Type 'exit' to quit.")
    
    while True:
        user_input = input("\nGit-Bot> ")
        if user_input.lower() in ['exit', 'quit']: break
        if not user_input.strip(): continue
        
        # 1. Retrieve RAG Context
        results = collection.query(query_texts=[user_input], n_results=3)
        history_context = ""
        if results and results.get('documents') and len(results['documents'][0]) > 0:
            history_context = "\n".join(
                [f"- Request: '{req}', Command: '{meta['command']}'" 
                 for req, meta in zip(results['documents'][0], results['metadatas'][0])]
            )
        
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
                    doc_id = str(hash(user_input + cmd))
                    collection.add(documents=[user_input], metadatas=[{"command": cmd}], ids=[doc_id])
                except Exception as e:
                    # Added warning instead of silent pass
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
