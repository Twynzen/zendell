# zendell/agents/clarifier.py

import json
from datetime import datetime
from zendell.services.llm_provider import ask_gpt
from zendell.core.db import MongoDBManager

def clarifier_node(global_state: dict) -> dict:
    last_msg = global_state.get("last_message", "")
    activities = global_state.get("activities", [])
    if not last_msg or not activities:
        global_state["clarification_questions"] = []
        return global_state
    prompt = (
        f"Analiza el mensaje: '{last_msg}'. Se registraron las siguientes actividades: {activities}. "
        "Para cada actividad, identifica ambigüedades en contexto, intención, duración o detalles específicos. "
        "Genera al menos dos preguntas de clarificación específicas para cada actividad. Si en alguna actividad se menciona un nombre propio, "
        "genera también una pregunta adicional para profundizar en quién es esa persona y su rol. "
        "Finalmente, formula una pregunta final que indique el cierre de esta interacción, preguntando si el usuario tiene algo más que aclarar o agregar antes de finalizar esta hora. "
        "Devuelve únicamente un JSON válido EXACTAMENTE en el siguiente formato (sin texto adicional): "
        '{"questions": ["Pregunta 1", "Pregunta 2", ...]} '
        "Si no se pueden generar preguntas, devuelve: {\"questions\": []}."
    )
    response = ask_gpt(prompt)
    try:
        data = json.loads(response.strip())
        questions = data.get("questions", [])
    except Exception as e:
        print(f"[clarifier] Error al parsear la respuesta: {e}")
        questions = ["¿Podrías aclarar más detalles sobre estas actividades?"]
    global_state["clarification_questions"] = questions
    final_prompt = "Antes de concluir esta hora, ¿podrías responder si hay algo más que quieras aclarar o agregar sobre las actividades mencionadas?"
    global_state["clarification_final_prompt"] = final_prompt
    db = MongoDBManager()
    user_id = global_state.get("user_id", "")
    state = db.get_state(user_id)
    state.setdefault("clarifier_history", []).append({
        "timestamp": datetime.utcnow().isoformat(),
        "clarification_questions": questions,
        "final_prompt": final_prompt
    })
    db.save_state(user_id, state)
    return global_state
