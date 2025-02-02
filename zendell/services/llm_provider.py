# zendell/services/llm_provider.py

from openai import OpenAI
from typing import Optional, List, Dict, Any
from config.settings import OPENAI_API_KEY

# Configurar el cliente de OpenAI con la API key
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def ask_gpt(
    prompt: str,
    model: str = "gpt-4o",
    temperature: float = 0.7
) -> Optional[str]:
    """
    Envía un 'prompt' al modelo (estilo ChatCompletion) y retorna la respuesta de GPT.
    Usa el patrón 'openai_client.chat.completions.create' que solicitaste.
    """
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERROR] al preguntar a GPT: {e}")
        return None

def ask_gpt_chat(
    messages: List[Dict[str, str]],
    model: str = "gpt-4o",
    temperature: float = 0.7
) -> Optional[str]:
    """
    Envía una lista 'messages' (cada item con 'role' y 'content')
    y retorna la respuesta del 'assistant'.
    """
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERROR] al preguntar a GPT (chat mode): {e}")
        return None
