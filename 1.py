import os
import subprocess
import platform
import chromadb
import google.generativeai as genai

# Setup Gemini API
api_key = os.getenv("GEMINI_API_KEY")


genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# Setup ChromaDB for RAG (Command History)
# This will create a 'chroma_db' folder in the current directory to persist history.
chroma_client = chromadb.PersistentClient(path="./chroma_db")
# Using Chroma's default embedding function
collection = chroma_client.get_or_create_collection(name="command_history")

def get_system_context():
    os_name = platform.system()
    cwd = os.getcwd()
    shell_type = "Windows Command Prompt (cmd.exe)" if os.name == 'nt' else "Bash"
    return f"OS: {os_name}, Shell: {shell_type}, CWD: {cwd}"

def generate_command(user_input, context, history_context="", error_message=None, previous_cmd=None):
    # Extract shell type from context
    shell_type = "Windows Command Prompt (cmd.exe)" if "cmd.exe" in context else "Bash"
    
    prompt = f"""
You are an expert systems administrator and terminal assistant. Convert the user request into a valid, up-to-date {shell_type} command.

CRITICAL RULES:
1. ONLY output the raw command. 
2. DO NOT include markdown code blocks (e.g., no ```powershell or ```).
3. DO NOT include any explanations or conversational text.
4. Use modern, widely-supported commands. Ensure valid syntax for {shell_type}.

System Context:
{context}
"""
    if history_context:
        prompt += f"\nRelevant Past Commands (RAG Context - use as reference if similar):\n{history_context}\n"
    
    if error_message and previous_cmd:
        prompt += f"\nThe previous command `{previous_cmd}` failed with this error:\n{error_message}\nCarefully analyze the error and provide a CORRECTED command."
    
    prompt += f"\nUser Request: {user_input}"
    
    response = model.generate_content(prompt)
    cmd = response.text.strip()
    
    # Fallback to strip markdown if the model hallucinates it despite instructions
    cmd = cmd.replace("```powershell", "").replace("```bash", "").replace("```sh", "").replace("```", "").strip()
    return cmd

def ai_shell():
    print("AI Shell Initialized (with RAG & Agentic Auto-Correction). Type 'exit' to quit.")
    while True:
        user_input = input("AI-Admin> ")
        if user_input.lower() in ['exit', 'quit']: break
        if not user_input.strip(): continue
        
        # 1. Retrieve RAG Context
        # Querying the database for similar previous requests
        results = collection.query(
            query_texts=[user_input],
            n_results=3
        )
        
        history_context = ""
        # Format the RAG results if any exist
        if results and results.get('documents') and len(results['documents'][0]) > 0:
            history_context = "\n".join(
                [f"- Request: '{req}', Command: '{meta['command']}'" 
                 for req, meta in zip(results['documents'][0], results['metadatas'][0])]
            )
        
        context = get_system_context()
        error_msg = None
        current_cmd = None
        
        # 2. Agentic Loop (Generate -> Execute -> Correct)
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            cmd = generate_command(user_input, context, history_context, error_msg, current_cmd)
            current_cmd = cmd
            
            print(f"Executing: {cmd}")
            # Execute command and capture output/error for agentic correction
            process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            # Print output to user
            if process.stdout:
                print(process.stdout)
            
            if process.returncode == 0:
                # 3. Store Success in RAG
                try:
                    doc_id = str(hash(user_input + cmd))
                    # We only add if this specific interaction wasn't added before
                    collection.add(
                        documents=[user_input],
                        metadatas=[{"command": cmd}],
                        ids=[doc_id]
                    )
                    print("[Saved to RAG History]")
                except Exception as e:
                    # Ignore exceptions like duplicate ID
                    pass
                break # Success, exit agentic loop
            else:
                print(f"Execution Failed (Exit Code: {process.returncode}):")
                if process.stderr:
                    print(process.stderr)
                error_msg = process.stderr or "Unknown Error"
                
                print("Attempting auto-correction...")
                retry_count += 1
                
        if retry_count >= max_retries:
            print("Max auto-correction retries reached. Cancelling.")

if __name__ == "__main__":
    ai_shell()