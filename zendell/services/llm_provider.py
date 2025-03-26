# zendell/services/llm_provider.py

from openai import OpenAI
from typing import Optional, List, Dict, Any
from config.settings import OPENAI_API_KEY
from core.utils import get_timestamp

# Global variable to store the selected model
SELECTED_MODEL = "gpt-4o"

def set_global_model(model_name: str):
    """Set the global model to use for all LLM requests."""
    global SELECTED_MODEL
    SELECTED_MODEL = model_name
    print(f"{get_timestamp()}", f"[LLM_PROVIDER] Model set to: {SELECTED_MODEL}")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

def ask_gpt(prompt: str, model: str = None, temperature: float = 0.7) -> Optional[str]:
    # Use the global model if no specific model is provided
    model_to_use = model if model else SELECTED_MODEL
    
    try:
        response = openai_client.chat.completions.create(
            model=model_to_use,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"{get_timestamp()}", f"[ERROR] when asking GPT: {e}")
        return None

def ask_gpt_chat(messages: List[Dict[str, str]], model: str = None, temperature: float = 0.7) -> Optional[str]:
    # Use the global model if no specific model is provided
    model_to_use = model if model else SELECTED_MODEL
    
    try:
        response = openai_client.chat.completions.create(
            model=model_to_use,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"{get_timestamp()}", f"[ERROR] when asking GPT (chat mode): {e}")
        return None