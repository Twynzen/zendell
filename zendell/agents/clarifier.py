# zendell/agents/clarifier.py
from zendell.services.llm_provider import ask_gpt
import json

def clarifier_node(global_state: dict) -> dict:
    last_msg = global_state.get("last_message", "")
    activities = global_state.get("activities", [])
    prompt = (
        f"Analiza el mensaje: '{last_msg}'. Se registraron las siguientes actividades: {activities}. "
        "Para cada actividad, identifica si existen ambigüedades en contexto, intención, duración o detalles específicos. "
        "Genera al menos dos preguntas de clarificación específicas para cada actividad. Si es necesario, incluye una breve explicación del porqué se hacen las preguntas, especialmente si el usuario ha preguntado sobre el motivo de la pregunta. "
        "Devuelve **únicamente** un JSON válido EXACTAMENTE en el siguiente formato (sin texto adicional):\n"
        '{"questions": ["Pregunta 1", "Pregunta 2", ...]}\n'
        "Si no hay preguntas, devuelve: {\"questions\": []}."
    )
    response = ask_gpt(prompt)
    try:
        data = json.loads(response)
        questions = data.get("questions", [])
    except Exception as e:
        print(f"[clarifier] Error al parsear la respuesta: {e}")
        questions = ["¿Podrías aclarar más detalles sobre estas actividades?"]
    global_state["clarification_questions"] = questions
    return global_state
