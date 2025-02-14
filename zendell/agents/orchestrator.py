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
    context = f"El usuario se llama {name}. Últimas notas: {last_notes}. Etapa actual: {stage}. Tu objetivo es ayudarle y preguntarle sobre sus actividades. No hables en primera persona de tus propias acciones, no inventes datos sobre ti. Sé breve y conciso, y mantén coherencia con lo que el usuario te dijo."
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
            prompt = f"Hola {nombre}, para conocerte mejor necesito saber: {needed}. Por favor, proporciona estos datos de forma clara y completa."
            stage = "ask_profile"
            reply = ask_gpt_in_context(db, user_id, prompt, stage)
        else:
            stage = "ask_last_hour"
            prompt = f"Pregunta al usuario '{state['name']}' qué hizo entre {tmap['last_hour']['start']} y {tmap['last_hour']['end']}. No hables de tus actividades; hazle la pregunta de forma directa."
            reply = ask_gpt_in_context(db, user_id, prompt, stage)
    elif stage == "ask_profile":
        if missing:
            needed = ", ".join(missing)
            prompt = f"Aún faltan estos datos: {needed}. Por favor, proporciónalos de forma clara y sin agregar información extra."
            reply = ask_gpt_in_context(db, user_id, prompt, stage)
        else:
            stage = "ask_last_hour"
            prompt = f"Pregunta al usuario '{state['name']}' qué hizo entre {tmap['last_hour']['start']} y {tmap['last_hour']['end']}. No hables de tus actividades; hazle la pregunta de forma directa."
            reply = ask_gpt_in_context(db, user_id, prompt, stage)
    elif stage == "ask_last_hour":
        stage = "ask_next_hour"
        prompt = f"Ahora pídele a {state['name']} que cuente qué planea hacer entre {tmap['next_hour']['start']} y {tmap['next_hour']['end']}. No hables de tus actividades; hazle la pregunta de forma directa."
        reply = ask_gpt_in_context(db, user_id, prompt, stage)
    elif stage == "ask_next_hour":
        from zendell.agents.clarifier import clarifier_node
        global_state = clarifier_node(global_state)
        clarification_questions = global_state.get("clarification_questions", [])
        if clarification_questions:
            prompt = "Para afinar detalles, necesito aclarar lo siguiente: " + "; ".join(clarification_questions)
            reply = ask_gpt_in_context(db, user_id, prompt, "clarifier_pending")
        else:
            prompt = "No se generaron preguntas de clarificación relevantes. ¿Hay algo más que quieras aclarar?"
            reply = ask_gpt_in_context(db, user_id, prompt, "clarifier_pending")
    elif stage == "clarifier_pending":
        from zendell.agents.clarifier import process_clarifier_response
        global_state = process_clarifier_response(global_state)
        lower_msg = last_message.lower()
        if "no te he pedido" in lower_msg or "no he pedido" in lower_msg:
            stage = "final"
            prompt = "Entendido, procederé sin más aclaraciones. ¿Hay algo más en lo que pueda ayudarte, Armando?"
            reply = ask_gpt_in_context(db, user_id, prompt, stage)
        elif last_message.strip().endswith("?"):
            question_reply = ask_gpt_in_context(db, user_id, f"Responde de forma clara y concisa la siguiente pregunta: {last_message}", "final_question")
            stage = "final"
            prompt = f"{question_reply} ¿Puedo ayudarte con algo más, Armando?"
            reply = ask_gpt_in_context(db, user_id, prompt, stage)
        else:
            confirm_prompt = "He registrado que has aclarado: " + " ".join(global_state.get("clarifier_responses", [])) + ". ¿Es correcto?"
            reply = ask_gpt_in_context(db, user_id, confirm_prompt, "confirm_clarifier")
            stage = "confirm_clarifier"
    elif stage == "confirm_clarifier":
        if "si" in last_message.lower() or "correcto" in last_message.lower():
            stage = "final"
            final_prompt = "Perfecto, ¿hay algo más en lo que pueda ayudarte o alguna otra aclaración que necesites?"
            reply = ask_gpt_in_context(db, user_id, final_prompt, stage)
        else:
            stage = "final"
            final_prompt = "Entendido, ¿en qué más puedo ayudarte?"
            reply = ask_gpt_in_context(db, user_id, final_prompt, stage)
    elif stage == "final":
        if "?" in last_message.strip():
            question_reply = ask_gpt_in_context(db, user_id, f"Responde de forma precisa y amigable la siguiente pregunta: {last_message}", "final_question")
            reply = question_reply + "\n" + ask_gpt_in_context(db, user_id, "¿Hay algo más en lo que pueda ayudarte?", "final")
        else:
            reply = ask_gpt_in_context(db, user_id, "Ofrece un cierre o pregunta final para ver en qué más puedes ayudar.", "final")
    else:
        stage = "final"
        reply = ask_gpt_in_context(db, user_id, "Ofrece un cierre o pregunta final para ver en qué más puedes ayudar.", "final")
    state["conversation_stage"] = stage
    db.save_state(user_id, state)
    db.save_conversation_message(user_id, "assistant", reply, {"step": "orchestrator_flow"})
    return {"global_state": global_state, "final_text": reply}
