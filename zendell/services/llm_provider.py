# zendell/services/llm_provider.py

from openai import OpenAI
from typing import Optional, List, Dict, Any
from config.settings import OPENAI_API_KEY
from core.utils import get_timestamp

openai_client = OpenAI(api_key=OPENAI_API_KEY)

def ask_gpt(prompt: str, model: str = "gpt-4o", temperature: float = 0.7) -> Optional[str]:
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"{get_timestamp()}",f"[ERROR] al preguntar a GPT: {e}")
        return None

def ask_gpt_chat(messages: List[Dict[str, str]], model: str = "gpt-4o", temperature: float = 0.7) -> Optional[str]:
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"{get_timestamp()}",f"[ERROR] al preguntar a GPT (chat mode): {e}")
        return None