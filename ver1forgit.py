import os
import csv
import subprocess
import platform
import chromadb
import google.generativeai as genai

# Setup Gemini API
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# Setup ChromaDB for RAG (Git Command History)
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="command_history")

def ingest_git_data():
    if os.path.exists('git_cheat_sheet.csv'):
        print("Loading Git Cheat Sheet into RAG...")
        with open('git_cheat_sheet.csv', mode='r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            docs = []
            metadatas = []
            ids = []
            for index, row in enumerate(csv_reader):
                docs.append(row['Task'])
                metadatas.append({"command": row['Command']})
                ids.append(f"git_cheat_sheet_{index}")
            collection.add(documents=docs, metadatas=metadatas, ids=ids)
        print("Git data loaded successfully.")

def get_system_context():
    os_name = platform.system()
    cwd = os.getcwd()
    shell_type = "Windows Command Prompt (cmd.exe)" if os.name == 'nt' else "Bash"
    return f"OS: {os_name}, Shell: {shell_type}, CWD: {cwd}"

def generate_command(user_input, context, history_context="", error_message=None, previous_cmd=None):
    shell_type = "Windows Command Prompt (cmd.exe)" if "cmd.exe" in context else "Bash"
    prompt = f"""
You are an expert Git version control assistant. Convert the user request into a valid, up-to-date Git command.

CRITICAL RULES:
1. ONLY output the raw Git command (it should almost always start with 'git ').
2. DO NOT include markdown code blocks (e.g., no ```bash or ```).
3. DO NOT include any explanations or conversational text.
4. Only generate commands related to Git. If the user asks for something unrelated, output 'echo "Error: I only handle Git commands."'

System Context:
{context}
"""
    if history_context:
        prompt += f"\nRelevant Past Git Commands (RAG Context):\n{history_context}\n"
    if error_message and previous_cmd:
        prompt += f"\nThe previous command `{previous_cmd}` failed with this error:\n{error_message}\nCarefully analyze the error and provide a CORRECTED Git command."
    prompt += f"\nUser Request: {user_input}"
    response = model.generate_content(prompt)
    cmd = response.text.strip()
    cmd = cmd.replace("```powershell", "").replace("```bash", "").replace("```sh", "").replace("```", "").strip()
    return cmd

def ai_shell():
    ingest_git_data()
    print("\nGit AI Assistant Initialized (with RAG & Agentic Auto-Correction). Type 'exit' to quit.")
    while True:
        user_input = input("Git-Bot> ")
        if user_input.lower() in ['exit', 'quit']: break
        if not user_input.strip(): continue
        
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
        
        while retry_count < max_retries:
            cmd = generate_command(user_input, context, history_context, error_msg, current_cmd)
            current_cmd = cmd
            print(f"Executing: {cmd}")
            process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if process.stdout: print(process.stdout)
            
            if process.returncode == 0:
                try:
                    doc_id = str(hash(user_input + cmd))
                    collection.add(documents=[user_input], metadatas=[{"command": cmd}], ids=[doc_id])
                except Exception:
                    pass
                break
            else:
                print(f"Execution Failed (Exit Code: {process.returncode}):")
                if process.stderr: print(process.stderr)
                error_msg = process.stderr or "Unknown Error"
                print("Attempting auto-correction...")
                retry_count += 1
        if retry_count >= max_retries:
            print("Max auto-correction retries reached. Cancelling.")

if __name__ == "__main__":
    ai_shell()
