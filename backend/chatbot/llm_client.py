import os
import requests

class UnifiedLLMClient:
    """
    Unified LLM Client:
    - If GROQ_API_KEY is defined in environment variables, uses the free Groq Cloud API.
    - Otherwise, falls back to the local Ollama instance (e.g. http://127.0.0.1:11434).
    """
    def __init__(self, ollama_host=None):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        
        if self.groq_api_key:
            self.mode = "groq"
            self.groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
            print(f"[LLM] Active mode: GROQ Cloud API (preferred model: {self.groq_model})")
        else:
            self.mode = "ollama"
            try:
                from ollama import Client as OllamaClient
                self.ollama_client = OllamaClient(host=self.ollama_host)
                print(f"[LLM] Active mode: Local OLLAMA ({self.ollama_host})")
            except Exception as e:
                print(f"[LLM] Warning: Ollama client initialization error: {e}")
                self.ollama_client = None

    def chat(self, model="llama3.2", messages=None, **kwargs):
        if messages is None:
            messages = []

        if self.mode == "groq":
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.groq_api_key.strip()}",
                "Content-Type": "application/json"
            }
            # Candidate models to try in order of capability
            candidates = [self.groq_model, "llama-3.1-8b-instant", "llama-3.2-3b-preview"]
            # Deduplicate while preserving order
            models_to_try = []
            for m in candidates:
                if m not in models_to_try:
                    models_to_try.append(m)

            last_error = None
            for candidate in models_to_try:
                try:
                    payload = {
                        "model": candidate,
                        "messages": messages,
                        "temperature": kwargs.get("temperature", 0.3)
                    }
                    response = requests.post(url, headers=headers, json=payload, timeout=25)
                    if response.status_code == 200:
                        data = response.json()
                        content = data["choices"][0]["message"]["content"]
                        return {
                            "message": {
                                "role": "assistant",
                                "content": content
                            }
                        }
                    else:
                        print(f"[LLM] Groq model '{candidate}' returned {response.status_code}: {response.text}")
                        last_error = f"{response.status_code} - {response.text}"
                except Exception as ex:
                    print(f"[LLM] Groq request error with '{candidate}': {ex}")
                    last_error = str(ex)

            # If all Groq models failed, return graceful response instead of crashing with 500
            print(f"[LLM] All Groq candidates failed. Last error: {last_error}")
            return {
                "message": {
                    "role": "assistant",
                    "content": "I apologize, but I am having temporary trouble reaching the language model right now. Please try your question again in a moment!"
                }
            }
        else:
            if not self.ollama_client:
                from ollama import Client as OllamaClient
                self.ollama_client = OllamaClient(host=self.ollama_host)
            return self.ollama_client.chat(model=model, messages=messages, **kwargs)

def get_llm_client():
    return UnifiedLLMClient()
