# zendell/agents/orchestrator.py

from typing import Dict, Any
from datetime import datetime, timedelta
from zendell.services.llm_provider import ask_gpt_chat
from zendell.agents.activity_collector import activity_collector_node

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
        "last_hour": {"start": (now - timedelta(hours=1)).strftime("%H:%M"), "end": now.strftime("%H:%M")},
        "next_hour": {"start": now.strftime("%H:%M"), "end": (now + timedelta(hours=1)).strftime("%H:%M")}
    }

def build_system_context(db, user_id: str, stage: str) -> str:
    state = db.get_state(user_id)
    name = state.get("name", "Desconocido")
    st_info = state.get("short_term_info", [])
    last_notes = ". ".join(st_info[-3:]) if st_info else ""
    context = (
        f"ETAPA: {stage}. Usuario: {name}. Últimas notas: {last_notes}. "
        "Objetivo: Recopilar información y mantener una conversación fluida y natural. "
        "En 'ask_last_hour', pregunta qué hizo el usuario en la última hora, "
        "y si es necesario pide detalles. "
        "En 'clarifier_last_hour', profundiza con preguntas de clarificación (qué, cuándo, dónde, con quién, por qué). "
        "En 'ask_next_hour', pregunta por planes de la próxima hora. "
        "En 'clarifier_next_hour', profundiza con preguntas sobre esos planes. "
        "Evita negar ayuda; sé amigable y curioso para obtener datos claros."
    )
    return context


def ask_gpt_in_context(db, user_id: str, user_prompt: str, stage: str) -> str:
    system_text = build_system_context(db, user_id, stage)
    logs = db.get_user_conversation(user_id, limit=8)
    chat = [{"role": "system", "content": system_text}]
    for msg in logs:
        role = "assistant" if msg["role"] == "assistant" else "user"
        chat.append({"role": role, "content": msg["content"]})
    chat.append({"role": "user", "content": user_prompt})
    db.save_conversation_message(user_id, "system", f"GPT Prompt: {chat}", {"step": stage})
    response = ask_gpt_chat(chat, model="gpt-3.5-turbo", temperature=0.7)
    return response if response else "¿Podrías repetirme lo que necesitas?"

def orchestrator_flow(user_id: str, last_message: str, db_manager) -> Dict[str, Any]:
    db = db_manager
    state = db.get_state(user_id)
    stage = state.get("conversation_stage", "initial")
    
    print(f"[ORCHESTRATOR] START => user_id={user_id}, stage={stage}, last_message='{last_message}'")
    
    global_state = {
        "user_id": user_id,
        "customer_name": state.get("name", "Desconocido"),
        "activities": [],
        "analysis": {},
        "clarification_questions": [],
        "clarifier_responses": [],
        "last_message": last_message,
        "conversation_context": [],
        "db": db
    }

    # EJEMPLO: imprimir si existe override
    if state.get("conversation_stage_override"):
        print(f"[ORCHESTRATOR] Detected conversation_stage_override={state['conversation_stage_override']}")
        stage = state["conversation_stage_override"]

    # 1) Llamar al collector
    print(f"[ORCHESTRATOR] activity_collector_node => stage={stage}")
    global_state = activity_collector_node(global_state)
    
    # 2) Volver a cargar state (pudo cambiar en collector)
    state = db.get_state(user_id)
    missing = missing_profile_fields(state)
    tmap = get_time_ranges()
    reply = ""

    print(f"[ORCHESTRATOR] missing fields={missing}, time_ranges={tmap}, current_stage={stage}")

    if stage == "initial":
        if missing:
            needed = ", ".join(missing)
            prompt = f"Hola {state.get('name','amigo')}, para conocerte mejor necesito saber: {needed}. Proporciónalos de forma clara."
            stage = "ask_profile"
            print(f"[ORCHESTRATOR] => Transicion a stage={stage}, prompt='{prompt}'")
            reply = ask_gpt_in_context(db, user_id, prompt, stage)
        else:
            stage = "ask_last_hour"
            prompt = f"¿Qué hiciste entre las {tmap['last_hour']['start']} y las {tmap['last_hour']['end']}, {state['name']}?"
            print(f"[ORCHESTRATOR] => Transicion a stage={stage}, prompt='{prompt}'")
            reply = ask_gpt_in_context(db, user_id, prompt, stage)
    
    elif stage == "ask_profile":
        if missing:
            needed = ", ".join(missing)
            prompt = f"Aún faltan estos datos: {needed}. Proporciónalos de forma clara."
            print(f"[ORCHESTRATOR] => Repite stage={stage}, prompt='{prompt}'")
            reply = ask_gpt_in_context(db, user_id, prompt, stage)
        else:
            stage = "ask_last_hour"
            prompt = f"¿Qué hiciste entre las {tmap['last_hour']['start']} y las {tmap['last_hour']['end']}, {state['name']}?"
            print(f"[ORCHESTRATOR] => Transicion a stage={stage}, prompt='{prompt}'")
            reply = ask_gpt_in_context(db, user_id, prompt, stage)
    
    elif stage == "ask_last_hour":
        stage = "clarifier_last_hour"
        global_state["current_period"] = "past"
        from zendell.agents.clarifier import clarifier_node
        global_state = clarifier_node(global_state)
        questions = global_state.get("clarification_questions", [])
        if questions:
            prompt = "Para afinar detalles del período pasado, " + "; ".join(questions)
            print(f"[ORCHESTRATOR] => clarifier_last_hour, prompt='{prompt}'")
            reply = ask_gpt_in_context(db, user_id, prompt, "clarifier_last_hour")
        else:
            reply = "No se generaron preguntas de clarificación para el período pasado."
    
    elif stage == "clarifier_last_hour":
        from zendell.agents.clarifier import process_clarifier_response
        global_state = process_clarifier_response(global_state)
        stage = "ask_next_hour"
        prompt = f"¿Qué planeas hacer entre las {tmap['next_hour']['start']} y las {tmap['next_hour']['end']}, {state['name']}?"
        print(f"[ORCHESTRATOR] => Transicion a stage={stage}, prompt='{prompt}'")
        reply = ask_gpt_in_context(db, user_id, prompt, stage)
    
    elif stage == "ask_next_hour":
        stage = "clarifier_next_hour"
        global_state["current_period"] = "future"
        from zendell.agents.clarifier import clarifier_node
        global_state = clarifier_node(global_state)
        questions = global_state.get("clarification_questions", [])
        if questions:
            prompt = "Para afinar detalles del período futuro, " + "; ".join(questions)
            print(f"[ORCHESTRATOR] => clarifier_next_hour, prompt='{prompt}'")
            reply = ask_gpt_in_context(db, user_id, prompt, "clarifier_next_hour")
        else:
            reply = "No se generaron preguntas de clarificación para el período futuro."
    
    elif stage == "clarifier_next_hour":
        from zendell.agents.clarifier import process_clarifier_response
        global_state = process_clarifier_response(global_state)
        stage = "final"
        prompt = "Perfecto. He registrado todo. ¿Hay algo más que quieras comentar o alguna otra meta a futuro?"
        print(f"[ORCHESTRATOR] => Transicion a stage={stage}, prompt='{prompt}'")
        reply = ask_gpt_in_context(db, user_id, prompt, stage)
    
    elif stage == "final":
        reply = ask_gpt_in_context(db, user_id, "Cierro la conversación, todo registrado. ¡Gracias!", "final")
    else:
        stage = "final"
        reply = ask_gpt_in_context(db, user_id, "Información final registrada. Hasta luego.", "final")

    state["conversation_stage"] = stage
    db.save_state(user_id, state)

    # Guardar en logs la respuesta final de la IA
    db.save_conversation_message(user_id, "assistant", reply, {"step": stage})
    
    print(f"[ORCHESTRATOR] END => new_stage={stage}, reply='{reply[:60]}...'")
    return {"global_state": global_state, "final_text": reply}
