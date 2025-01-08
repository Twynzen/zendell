# /services/llm_provider.py

from openai import OpenAI
from typing import Optional
from config.settings import OPENAI_API_KEY

# Configurar el cliente de OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def ask_gpt(
    prompt: str,
    model: str = "gpt-3.5-turbo",
    temperature: float = 0.7
) -> Optional[str]:
    """
    Envía un mensaje 'prompt' al modelo de OpenAI y devuelve la respuesta como string.
    - prompt: texto que enviaremos al modelo.
    - model: nombre del modelo a usar (ej: gpt-4, gpt-3.5-turbo, etc.).
    - temperature: control de creatividad (0 = menos creativo, 1 = más creativo).
    """
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature
        )
        # Accedemos correctamente al contenido de la respuesta
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[ERROR] al preguntar a GPT: {e}")
        return None
