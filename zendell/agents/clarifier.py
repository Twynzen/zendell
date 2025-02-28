# zendell/agents/clarifier.py

import json
from datetime import datetime
from zendell.services.llm_provider import ask_gpt

def clarifier_node(global_state: dict) -> dict:
    last_msg = global_state.get("last_message", "")
    activities = global_state.get("activities", [])
    if not last_msg or not activities:
        global_state["clarification_questions"] = []
        return global_state
    prompt = (
        f"Analiza el siguiente mensaje del usuario: '{last_msg}'. "
        f"Se detectaron estas actividades: {activities}. "
        "Determina qué detalles o información relevante faltan para comprender cada actividad con mayor profundidad, "
        "considerando aspectos como: quién participó, qué sucedió exactamente, cuándo, dónde, cómo y por qué. "
        "No preguntes algo que ya se haya mencionado en el mensaje. "
        "Genera hasta 3 preguntas de clarificación específicas y directas, enfocadas únicamente en la información que aún no está clara. "
        "Devuelve un JSON EXACTO en el siguiente formato (sin texto adicional): "
        '{"questions": ["Pregunta 1", "Pregunta 2", "Pregunta 3"]}. '
        "Si no se necesitan preguntas de clarificación, devuelve: {\"questions\": []}."
    )
    response = ask_gpt(prompt)
    try:
        data = json.loads(response.strip())
        questions = data.get("questions", [])
        if len(questions) > 3:
            questions = questions[:3]
    except Exception:
        questions = ["¿Podrías dar más detalles sobre lo que sucedió?"]
    global_state["clarification_questions"] = questions
    final_prompt = "¿Hay algo más que quieras aclarar sobre estas actividades?"
    global_state["clarification_final_prompt"] = final_prompt
    db = global_state["db"]
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
    user_input = global_state.get("user_clarifier_response", global_state.get("last_message", ""))
    activities = global_state.get("activities", [])
    if not user_input or not activities:
        return global_state
    prompt = (
        f"Analiza la siguiente respuesta del usuario: '{user_input}' en el contexto de las actividades: {activities}. "
        "Extrae de forma concisa la información relevante que responda a las preguntas de clarificación pendientes. "
        "Si el usuario no aporta nada nuevo, devuélvelo tal cual. "
        "Luego, genera hasta dos posibles preguntas de clarificación adicionales si consideras que aún falta información esencial. "
        "Devuelve un JSON EXACTO con la estructura: "
        '{"clarifier_responses": ["Respuesta 1", "Respuesta 2"], "new_questions": ["Pregunta adicional"]}. '
        "Si no se extrae nada nuevo, o no hay más preguntas, deja esos campos vacíos o como arrays vacíos."
    )
    response = ask_gpt(prompt)
    try:
        data = json.loads(response.strip())
        extracted_responses = data.get("clarifier_responses", [])
        new_questions = data.get("new_questions", [])
    except Exception:
        extracted_responses = [user_input]
        new_questions = []
    if not extracted_responses:
        extracted_responses = [user_input]
    global_state["clarifier_responses"] = extracted_responses
    question_asked = global_state.get("clarification_questions", ["Pregunta sin identificar"])[0]
    structured_data = {
        "question": question_asked,
        "answer": user_input,
        "timestamp": datetime.utcnow().isoformat()
    }
    db = global_state["db"]
    user_id = global_state.get("user_id", "")
    for activity in activities:
        activity_id = activity.get("activity_id")
        if activity_id:
            db.activities_coll.update_one({"activity_id": activity_id}, {"$push": {"clarifier_responses": structured_data}})
    state = db.get_state(user_id)
    state.setdefault("clarifier_history", []).append({
        "timestamp": datetime.utcnow().isoformat(),
        "structured_response": structured_data,
        "new_questions": new_questions
    })
    db.save_state(user_id, state)
    return global_state