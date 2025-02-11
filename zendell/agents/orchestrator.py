# zendell/agents/orchestrator.py
from typing import Dict, Any
from datetime import datetime, timedelta
from zendell.core.db import MongoDBManager
from zendell.agents.activity_collector import activity_collector_node
from zendell.services.llm_provider import ask_gpt_chat, ask_gpt

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
    context = (
        f"El usuario se llama {name}. Últimas notas: {last_notes}. Etapa actual: {stage}. "
        "Tu objetivo es ayudarle y preguntarle sobre sus actividades. "
        "No hables en primera persona de tus propias acciones, no inventes datos sobre ti. "
        "Sé breve y conciso, y mantén coherencia con lo que el usuario te dijo."
    )
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
        # Uso del LLM para analizar semánticamente si el usuario cuestiona el motivo de la pregunta
        meta_check_prompt = (
            f"Analiza el siguiente mensaje del usuario: '{last_message}'. "
            "¿El usuario está cuestionando el motivo de la pregunta que se le hizo anteriormente? "
            "Responde únicamente con 'Sí' o 'No'."
        )
        meta_check_response = ask_gpt(meta_check_prompt)
        if meta_check_response.strip().lower() == "sí":
            friendly_prompt = (
                "Genera una respuesta amistosa y empática que explique brevemente que la razón de la pregunta es "
                "conocer mejor sus experiencias para poder ayudarle de forma personalizada, tal como lo haría un buen amigo. "
                "Responde de forma natural y cercana."
            )
            friendly_response = ask_gpt(friendly_prompt)
            db.save_conversation_message(user_id, "assistant", friendly_response, {"step": "orchestrator_flow_extra"})
        stage = "ask_next_hour"
        prompt = f"Ahora pídele a {state['name']} que cuente qué planea hacer entre {tmap['next_hour']['start']} y {tmap['next_hour']['end']}. No hables de tus actividades; hazle la pregunta de forma directa."
        reply = ask_gpt_in_context(db, user_id, prompt, stage)
    elif stage == "ask_next_hour":
        stage = "clarify"
        from zendell.agents.clarifier import clarifier_node
        global_state = clarifier_node(global_state)
        clarification_questions = global_state.get("clarification_questions", [])
        if clarification_questions:
            prompt = "Para afinar detalles, necesito aclarar lo siguiente: " + "; ".join(clarification_questions)
            reply = ask_gpt_in_context(db, user_id, prompt, stage)
        else:
            final_prompt = "Ofrece un cierre amigable e invita al usuario a seguir conversando si lo desea. Sé creativo y evita mensajes predefinidos."
            reply = ask_gpt_in_context(db, user_id, final_prompt, stage)
    elif stage == "clarify":
        stage = "final"
        final_prompt = "Ofrece un cierre o pregunta final para ver en qué más puedes ayudar."
        reply = ask_gpt_in_context(db, user_id, final_prompt, stage)
    else:
        stage = "final"
        final_prompt = "Ofrece un cierre o pregunta final para ver en qué más puedes ayudar."
        reply = ask_gpt_in_context(db, user_id, final_prompt, stage)
    state["conversation_stage"] = stage
    db.save_state(user_id, state)
    db.save_conversation_message(user_id, "assistant", reply, {"step": "orchestrator_flow"})
    return {"global_state": global_state, "final_text": reply}
