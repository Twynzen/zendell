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
        "Para cada actividad, identifica ambigüedades relevantes en contexto, intención, duración y detalles específicos, considerando el marco temporal de la actividad. "
        "Genera máximo 3 preguntas de clarificación de mayor prioridad y breves, evitando preguntas genéricas o irrelevantes. "
        "Devuelve únicamente un JSON válido EXACTAMENTE en el siguiente formato (sin texto adicional): "
        '{"questions": ["Pregunta 1", "Pregunta 2", ...]} '
        "Si no se pueden generar preguntas, devuelve: {\"questions\": []}."
    )
    response = ask_gpt(prompt)
    try:
        data = json.loads(response.strip())
        questions = data.get("questions", [])
    except Exception:
        questions = ["¿Podrías aclarar más detalles sobre las actividades?"]
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

def process_clarifier_response(global_state: dict) -> dict:
    user_response = global_state.get("last_message", "")
    activities = global_state.get("activities", [])
    if not user_response or not activities:
        return global_state
    prompt = (
        f"Analiza la siguiente respuesta del usuario: '{user_response}' en el contexto de las actividades: {activities}. "
        "Extrae de forma concisa la información relevante y genera al menos dos respuestas de clarificación que aporten detalles útiles sobre las actividades mencionadas. "
        "Devuelve únicamente un JSON válido EXACTAMENTE en el siguiente formato (sin texto adicional): "
        '{"clarifier_responses": ["Respuesta 1", "Respuesta 2", ...]} '
        "Si no se puede extraer información, devuelve: {\"clarifier_responses\": []}."
    )
    response = ask_gpt(prompt)
    try:
        data = json.loads(response.strip())
        clarifier_responses = data.get("clarifier_responses", [])
        if not clarifier_responses:
            raise ValueError
    except Exception:
        clarifier_responses = [user_response]
    global_state["clarifier_responses"] = clarifier_responses
    db = MongoDBManager()
    user_id = global_state.get("user_id", "")
    for activity in activities:
        activity_id = activity.get("activity_id")
        if activity_id:
            db.activities_coll.update_one(
                {"activity_id": activity_id},
                {"$push": {"clarifier_responses": {"responses": clarifier_responses, "timestamp": datetime.utcnow().isoformat()}}}
            )
    state = db.get_state(user_id)
    state.setdefault("clarifier_history", []).append({
        "timestamp": datetime.utcnow().isoformat(),
        "clarifier_responses": clarifier_responses,
        "user_response": user_response
    })
    db.save_state(user_id, state)
    return global_state
