# agents/conversation_analyzer.py
from typing import Dict, Any
from services.llm_provider import ask_gpt
import json

def analyze_conversation_flow(db_manager, user_id: str, limit: int = 20) -> Dict[str, Any]:
    """
    Lee los últimos 'limit' mensajes de la conversación y llama al LLM para 
    obtener un resumen del estado actual del usuario, su mood y si desea terminar.
    Devuelve un dict con { 'overall_mood': ..., 'wants_to_stop': bool, 'summary': '...' }.
    """
    messages = db_manager.get_conversation_history(user_id, limit=limit)
    # Construimos un prompt con todo el historial
    # Podrías filtrar solo user messages, o incluir los del bot, etc.
    conversation_text = ""
    for msg in messages:
        speaker = "Bot" if msg["is_bot"] else "User"
        conversation_text += f"{speaker} ({msg['timestamp']}): {msg['message']}\n"

    # LLM Prompt orientado a un “macro-análisis”
    prompt = f"""
Eres un analista de conversaciones. Aquí tienes el historial reciente:

{conversation_text}

Analiza la charla y responde en JSON con:
- "overall_mood": la emoción predominante del usuario (ej: 'triste', 'negativo', 'cansado', 'positivo', etc.)
- "wants_to_stop": un boolean (true o false) indicando si el usuario quiere ya no hablar más
- "summary": un breve resumen del estado actual

Solo responde en JSON válido, sin texto extra.
"""

    llm_response = ask_gpt(prompt)
    # Parseamos el JSON
    print("[ConversationAnalyzer] Respuesta del LLM:", llm_response)
    try:
        result = json.loads(llm_response)
    except:
        result = {
            "overall_mood": "neutral",
            "wants_to_stop": False,
            "summary": "No se pudo parsear la respuesta del LLM."
        }
    return result
