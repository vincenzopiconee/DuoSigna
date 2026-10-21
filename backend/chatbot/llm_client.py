import os
import requests

class UnifiedLLMClient:
    """
    Unified LLM Client:
    - If GROQ_API_KEY is defined in environment variables, dynamically discovers available Groq models and uses the active one.
    - Otherwise, falls back to the local Ollama instance (e.g. http://127.0.0.1:11434).
    """
    def __init__(self, ollama_host=None):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        self.discovered_model = None
        
        if self.groq_api_key:
            self.mode = "groq"
            print("[LLM] Active mode: GROQ Cloud API")
            self._discover_active_model()
        else:
            self.mode = "ollama"
            try:
                from ollama import Client as OllamaClient
                self.ollama_client = OllamaClient(host=self.ollama_host)
                print(f"[LLM] Active mode: Local OLLAMA ({self.ollama_host})")
            except Exception as e:
                print(f"[LLM] Warning: Ollama client initialization error: {e}")
                self.ollama_client = None

    def _discover_active_model(self):
        """Query Groq /models endpoint to find which models are active for this API key."""
        if not self.groq_api_key:
            return
        
        headers = {
            "Authorization": f"Bearer {self.groq_api_key.strip()}",
            "Content-Type": "application/json"
        }
        try:
            resp = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                all_model_ids = [m.get("id") for m in data if m.get("id")]
                print(f"[LLM] Live Groq models for this API key: {all_model_ids}")

                # Exclude whisper, audio, tts, and prompt-guard models
                chat_models = [
                    m for m in all_model_ids
                    if not any(k in m.lower() for k in ["whisper", "guard", "orpheus", "tts", "embedding"])
                ]

                # Priority preferences among known quality models
                priority = [
                    "llama-3.3-70b-versatile",
                    "llama-3.1-8b-instant",
                    "llama-3.1-70b-versatile",
                    "openai/gpt-oss-20b",
                    "openai/gpt-oss-120b",
                    "mixtral-8x7b-32768",
                    "gemma2-9b-it",
                    "qwen/qwen3.8-27b"
                ]

                for p in priority:
                    if p in chat_models:
                        self.discovered_model = p
                        print(f"[LLM] Selected preferred active model: {self.discovered_model}")
                        return

                if chat_models:
                    self.discovered_model = chat_models[0]
                    print(f"[LLM] Selected first available chat model: {self.discovered_model}")
                    return
            else:
                print(f"[LLM] Warning: Could not list Groq models ({resp.status_code}): {resp.text}")
        except Exception as e:
            print(f"[LLM] Error discovering Groq models: {e}")

        # Fallback if discovery network fails
        self.discovered_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    def chat(self, model="llama3.2", messages=None, **kwargs):
        if messages is None:
            messages = []

        if self.mode == "groq":
            if not self.discovered_model:
                self._discover_active_model()

            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.groq_api_key.strip()}",
                "Content-Type": "application/json"
            }

            # Primary model to use
            primary_model = self.discovered_model or "llama-3.1-8b-instant"
            
            try:
                payload = {
                    "model": primary_model,
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
                    # If primary failed with 404 or decommissioned, re-discover and retry once
                    print(f"[LLM] Primary model {primary_model} returned {response.status_code}: {response.text}")
                    self._discover_active_model()
                    if self.discovered_model and self.discovered_model != primary_model:
                        payload["model"] = self.discovered_model
                        retry_resp = requests.post(url, headers=headers, json=payload, timeout=25)
                        if retry_resp.status_code == 200:
                            data = retry_resp.json()
                            content = data["choices"][0]["message"]["content"]
                            return {
                                "message": {
                                    "role": "assistant",
                                    "content": content
                                }
                            }
                    
                    return {
                        "message": {
                            "role": "assistant",
                            "content": f"I apologize, but I am having trouble reaching the AI model right now. (Groq Error: {response.status_code} - {response.text})"
                        }
                    }
            except Exception as ex:
                print(f"[LLM] Request error: {ex}")
                return {
                    "message": {
                        "role": "assistant",
                        "content": f"I apologize, but there was a connection error to the AI service: {str(ex)}"
                    }
                }
        else:
            if not self.ollama_client:
                from ollama import Client as OllamaClient
                self.ollama_client = OllamaClient(host=self.ollama_host)
            return self.ollama_client.chat(model=model, messages=messages, **kwargs)

def get_llm_client():
    return UnifiedLLMClient()
