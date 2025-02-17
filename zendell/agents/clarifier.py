# zendell/agents/clarifier.py

import json
from datetime import datetime
from zendell.services.llm_provider import ask_gpt
from zendell.core.db import MongoDBManager

def clarifier_node(global_state: dict) -> dict:
    last_msg = global_state.get("last_message", "")
    activities = global_state.get("activities", [])
    if not last_msg or not activities:
        print("[DEBUG] Clarifier Node: No hay mensaje o actividades para procesar.")
        global_state["clarification_questions"] = []
        return global_state
    prompt = (
        f"Analiza el mensaje: '{last_msg}'. Se registraron las siguientes actividades: {activities}. "
        "Para cada actividad, identifica ambigüedades específicas en contexto, intención, duración y detalles únicos. "
        "Genera hasta 3 preguntas de clarificación que sean precisas y útiles para obtener información detallada sobre la actividad. "
        "Considera preguntas sobre qué ocurrió, cuándo, dónde, cómo, con quién y por qué, pero no te limites a estos ejemplos. "
        "Devuelve únicamente un JSON válido EXACTAMENTE en el siguiente formato (sin texto adicional): "
        '{"questions": ["Pregunta 1", "Pregunta 2", "Pregunta 3"]} '
        "Si no se pueden generar preguntas, devuelve: {\"questions\": []}."
    )
    print(f"[DEBUG] Clarifier Node - Prompt enviado al LLM: {prompt}")
    response = ask_gpt(prompt)
    print(f"[DEBUG] Clarifier Node - Respuesta del LLM: {response}")
    try:
        data = json.loads(response.strip())
        questions = data.get("questions", [])
        if len(questions) > 3:
            questions = questions[:3]
    except Exception as e:
        print(f"[DEBUG] Clarifier Node - Error al parsear respuesta: {e}")
        questions = ["Por favor, proporciona detalles específicos sobre la actividad."]
    global_state["clarification_questions"] = questions
    final_prompt = "Antes de concluir, ¿hay algo adicional que quieras aclarar sobre estas actividades?"
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
    print(f"[DEBUG] Clarifier Node - Preguntas generadas: {questions}")
    return global_state

def process_clarifier_response(global_state: dict) -> dict:
    clarifier_input = global_state.get("clarifier_answer", global_state.get("last_message", ""))
    print(f"[DEBUG] Process Clarifier - Clarifier Input: {clarifier_input}")
    activities = global_state.get("activities", [])
    if not clarifier_input or not activities:
        print("[DEBUG] Process Clarifier - Falta clarifier_input o actividades.")
        return global_state
    prompt = (
        f"Analiza la siguiente respuesta del usuario: '{clarifier_input}' en el contexto de las actividades: {activities}. "
        "Extrae de forma concisa la información relevante y genera al menos dos respuestas de clarificación específicas y útiles, "
        "considerando dimensiones como qué, cuándo, dónde, cómo, con quién y por qué. "
        "Devuelve únicamente un JSON válido EXACTAMENTE en el siguiente formato (sin texto adicional): "
        '{"clarifier_responses": ["Respuesta 1", "Respuesta 2"]} '
        "Si no se puede extraer información, devuelve: {\"clarifier_responses\": []}."
    )
    print(f"[DEBUG] Process Clarifier - Prompt enviado al LLM: {prompt}")
    response = ask_gpt(prompt)
    print(f"[DEBUG] Process Clarifier - Respuesta del LLM: {response}")
    try:
        data = json.loads(response.strip())
        clarifier_responses = data.get("clarifier_responses", [])
        if not clarifier_responses:
            raise ValueError("Sin respuestas en JSON")
    except Exception as e:
        print(f"[DEBUG] Process Clarifier - Error al parsear respuesta: {e}")
        clarifier_responses = [clarifier_input]
    global_state["clarifier_responses"] = clarifier_responses
    question_respondida = global_state.get("clarification_questions", ["Pregunta sin identificar"])[0]
    structured_response = {
        "question": question_respondida,
        "answer": clarifier_input,
        "timestamp": datetime.utcnow().isoformat()
    }
    print(f"[DEBUG] Process Clarifier - Structured Response: {structured_response}")
    db = MongoDBManager()
    user_id = global_state.get("user_id", "")
    for activity in activities:
        if global_state.get("current_period") and activity.get("time_context") != global_state.get("current_period"):
            continue
        activity_id = activity.get("activity_id")
        if activity_id:
            db.activities_coll.update_one(
                {"activity_id": activity_id},
                {"$push": {"clarifier_responses": structured_response}}
            )
            print(f"[DEBUG] Process Clarifier - Actualizado activity_id {activity_id} con clarifier_responses.")
    state = db.get_state(user_id)
    state.setdefault("clarifier_history", []).append({
        "timestamp": datetime.utcnow().isoformat(),
        "structured_response": structured_response
    })
    db.save_state(user_id, state)
    return global_state
