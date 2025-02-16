# zendell/agents/orchestrator.py

from typing import Dict, Any
from datetime import datetime, timedelta
from zendell.core.db import MongoDBManager
from zendell.agents.activity_collector import activity_collector_node
from zendell.services.llm_provider import ask_gpt_chat

def missing_profile_fields(state: dict) -> list:
    fields = []
    if state.get("name", "Desconocido") in ["", "Desconocido"]:
        fields.append("nombre")
    info = state.get("general_info", {})
    if not info.get("ocupacion", ""):
        fields.append("ocupacion")
    if not info.get("gustos", ""):
        fields.append("gustos")
    if not info.get("metas", ""):
        fields.append("metas")
    return fields

def get_time_ranges() -> dict:
    now = datetime.now()
    return {
        "last_hour": {
            "start": (now - timedelta(hours=1)).strftime("%H:%M"),
            "end": now.strftime("%H:%M")
        },
        "next_hour": {
            "start": now.strftime("%H:%M"),
            "end": (now + timedelta(hours=1)).strftime("%H:%M")
        }
    }

def build_system_context(db: MongoDBManager, user_id: str, stage: str) -> str:
    state = db.get_state(user_id)
    name = state.get("name", "Desconocido")
    st_info = state.get("short_term_info", [])
    last_notes = ". ".join(st_info[-3:]) if st_info else ""
    context = f"El usuario se llama {name}. Últimas notas: {last_notes}. Etapa actual: {stage}. Tu objetivo es recopilar información sobre sus actividades sin ofrecer ayuda."
    return context

def ask_gpt_in_context(db: MongoDBManager, user_id: str, user_prompt: str, stage: str) -> str:
    system_text = build_system_context(db, user_id, stage)
    logs = db.get_user_conversation(user_id, limit=8)
    chat = [{"role": "system", "content": system_text}]
    for msg in logs:
        role = "assistant" if msg["role"] == "assistant" else "user"
        chat.append({"role": role, "content": msg["content"]})
    chat.append({"role": "user", "content": user_prompt})
    response = ask_gpt_chat(chat, model="gpt-3.5-turbo", temperature=0.7)
    return response if response else "¿Podrías repetirme lo que necesitas?"

def orchestrator_flow(user_id: str, last_message: str) -> Dict[str, Any]:
    db = MongoDBManager()
    state = db.get_state(user_id)
    stage = state.get("conversation_stage", "initial")
    global_state = {
        "user_id": user_id,
        "customer_name": state.get("name", "Desconocido"),
        "activities": [],
        "analysis": {},
        "clarification_questions": [],
        "clarifier_responses": [],
        "last_message": last_message,
        "conversation_context": []
    }
    global_state = activity_collector_node(global_state)
    state = db.get_state(user_id)
    missing = missing_profile_fields(state)
    tmap = get_time_ranges()
    reply = ""
    if stage == "initial":
        if missing:
            needed = ", ".join(missing)
            nombre = state.get("name", "amigo")
            prompt = f"Hola {nombre}, para conocerte mejor necesito saber: {needed}. Proporciónalos de forma clara."
            stage = "ask_profile"
            reply = ask_gpt_in_context(db, user_id, prompt, stage)
        else:
            stage = "ask_last_hour"
            prompt = f"Pregunta al usuario '{state['name']}' qué hizo entre {tmap['last_hour']['start']} y {tmap['last_hour']['end']}."
            reply = ask_gpt_in_context(db, user_id, prompt, stage)
    elif stage == "ask_profile":
        if missing:
            needed = ", ".join(missing)
            prompt = f"Aún faltan estos datos: {needed}. Proporciónalos de forma clara."
            reply = ask_gpt_in_context(db, user_id, prompt, stage)
        else:
            stage = "ask_last_hour"
            prompt = f"Pregunta al usuario '{state['name']}' qué hizo entre {tmap['last_hour']['start']} y {tmap['last_hour']['end']}."
            reply = ask_gpt_in_context(db, user_id, prompt, stage)
    elif stage == "ask_last_hour":
        stage = "clarifier_last_hour"
        from zendell.agents.clarifier import clarifier_node
        global_state = clarifier_node(global_state)
        clarification_questions = global_state.get("clarification_questions", [])
        if clarification_questions:
            prompt = "Para afinar detalles del período pasado, " + "; ".join(clarification_questions)
            reply = ask_gpt_in_context(db, user_id, prompt, "clarifier_last_hour")
        else:
            reply = "No se generaron preguntas de clarificación para el período pasado."
    elif stage == "clarifier_last_hour":
        from zendell.agents.clarifier import process_clarifier_response
        global_state = process_clarifier_response(global_state)
        stage = "ask_next_hour"
        prompt = f"Pregunta al usuario '{state['name']}' qué planea hacer entre {tmap['next_hour']['start']} y {tmap['next_hour']['end']}."
        reply = ask_gpt_in_context(db, user_id, prompt, stage)
    elif stage == "ask_next_hour":
        stage = "clarifier_next_hour"
        from zendell.agents.clarifier import clarifier_node
        global_state = clarifier_node(global_state)
        clarification_questions = global_state.get("clarification_questions", [])
        if clarification_questions:
            prompt = "Para afinar detalles del período futuro, " + "; ".join(clarification_questions)
            reply = ask_gpt_in_context(db, user_id, prompt, "clarifier_next_hour")
        else:
            reply = "No se generaron preguntas de clarificación para el período futuro."
    elif stage == "clarifier_next_hour":
        from zendell.agents.clarifier import process_clarifier_response
        global_state = process_clarifier_response(global_state)
        stage = "final"
        reply = "La información se ha registrado."
    elif stage == "final":
        reply = "La información se ha registrado."
    else:
        stage = "final"
        reply = "La información se ha registrado."
    state["conversation_stage"] = stage
    db.save_state(user_id, state)
    db.save_conversation_message(user_id, "assistant", reply, {"step": "orchestrator_flow"})
    return {"global_state": global_state, "final_text": reply}
