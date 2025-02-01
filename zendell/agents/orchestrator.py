# zendell/agents/orchestrator.py
from typing import Dict, Any
from datetime import datetime, timedelta
from zendell.core.db import MongoDBManager
from zendell.agents.activity_collector import activity_collector_node
from zendell.agents.analyzer import analyzer_node
from zendell.agents.recommender import recommender_node
from zendell.services.llm_provider import ask_gpt

def missing_profile_fields(user_state: dict) -> list:
    """
    Chequea si faltan: name, ocupacion, gustos, metas.
    Devuelve una lista con lo que falta.
    """
    missing = []
    if user_state.get("name", "Desconocido") in ["", "Desconocido"]:
        missing.append("name")
    general = user_state.get("general_info", {})
    if not general.get("ocupacion", ""):
        missing.append("ocupacion")
    if not general.get("gustos", ""):
        missing.append("gustos")
    if not general.get("metas", ""):
        missing.append("metas")
    return missing

def is_profile_complete(user_state: dict) -> bool:
    return len(missing_profile_fields(user_state)) == 0

def get_time_ranges() -> dict:
    """
    Retorna un dict con horas aproximadas para la última hora y la siguiente hora.
    """
    now = datetime.now()
    one_hour_ago = (now - timedelta(hours=1)).strftime("%H:%M")
    now_str = now.strftime("%H:%M")
    one_hour_future = (now + timedelta(hours=1)).strftime("%H:%M")

    return {
        "last_hour": {
            "start_time": one_hour_ago,
            "end_time": now_str
        },
        "next_hour": {
            "start_time": now_str,
            "end_time": one_hour_future
        }
    }

def orchestrator_flow(user_id: str, last_message: str) -> Dict[str, Any]:
    db_manager = MongoDBManager()
    user_state = db_manager.get_state(user_id)

    # Leemos o creamos el stage
    conversation_stage = user_state.get("conversation_stage", "initial")

    # Construimos el global_state. Le agregaremos "time_context" según la etapa
    global_state = {
        "user_id": user_id,
        "customer_name": user_state.get("name", "Desconocido"),
        "activities": [],
        "analysis": {},
        "recommendation": [],
        "last_message": last_message,
        "conversation_context": []
    }

    # 1) Llamamos activity_collector para parsear datos (nombre, actividades, etc.)
    global_state = activity_collector_node(global_state)
    # Releer user_state por si se guardaron más datos
    user_state = db_manager.get_state(user_id)

    # Chequeamos si ya se completó el perfil
    missing_fields = missing_profile_fields(user_state)
    profile_done = (len(missing_fields) == 0)

    # Tomamos rangos de hora
    time_map = get_time_ranges()

    # Comportamiento según stage
    if conversation_stage == "initial":
        # si ya está completo el perfil, pasamos a ask_last_hour
        if profile_done:
            conversation_stage = "ask_last_hour"
            # Guardamos en global_state que la siguiente respuesta describe la última hora
            global_state["time_context"] = "last_hour"
            global_state["time_range"] = time_map["last_hour"]

            # GPT: preguntamos qué hizo en la última hora
            assistant_reply = ask_gpt(build_prompt_ask_last_hour(last_message, user_state, global_state))
        else:
            # Falta algún dato => pedirlo
            assistant_reply = ask_gpt(build_prompt_missing_profile(last_message, user_state, missing_fields))

    elif conversation_stage == "ask_last_hour":
        # Ahora pasamos a ask_next_hour
        conversation_stage = "ask_next_hour"

        # Indicamos que la siguiente respuesta describe la próxima hora
        global_state["time_context"] = "next_hour"
        global_state["time_range"] = time_map["next_hour"]

        assistant_reply = ask_gpt(build_prompt_ask_next_hour(last_message, user_state, global_state))

    elif conversation_stage == "ask_next_hour":
        # Ya preguntamos la próxima hora => pasamos a final
        conversation_stage = "final"
        assistant_reply = ask_gpt(build_prompt_final(last_message, user_state))

    else:  # "final"
        # Podemos hacer analyzer + recommender
        global_state = analyzer_node(global_state)
        global_state = recommender_node(global_state)
        recs = global_state.get("recommendation", [])

        base_reply = ask_gpt(build_prompt_final(last_message, user_state))
        if not base_reply:
            base_reply = "Gracias por la info. ¿Deseas algo más?"
        if recs:
            assistant_reply = base_reply + "\n\nAquí tienes mis sugerencias:\n" + "\n".join(recs)
        else:
            assistant_reply = base_reply

    # Actualizamos stage y guardamos user_state
    user_state["conversation_stage"] = conversation_stage
    db_manager.save_state(user_id, user_state)

    # Guardamos assistant reply en conversation_logs
    db_manager.save_conversation_message(
        user_id=user_id,
        role="assistant",
        content=assistant_reply,
        extra_data={"step": "orchestrator_flow"}
    )

    return {
        "global_state": global_state,
        "final_text": assistant_reply
    }

# ---- PROMPTS ----

def build_prompt_missing_profile(last_message: str, user_state: dict, missing_fields: list) -> str:
    text_missing = ", ".join(missing_fields)
    prompt = (
        "Eres Zendell, un sistema multiagente en español. El usuario escribió:\n"
        f"'{last_message}'\n\n"
        "Sabes que te faltan estos datos de su perfil: "
        f"{text_missing}.\n"
        "Genera una respuesta amistosa y cordial, pidiéndole que comparta la información faltante. "
        "Muestra interés y disponibilidad para ayudar."
    )
    return prompt

def build_prompt_ask_last_hour(last_message: str, user_state: dict, global_state: dict) -> str:
    """
    Pregunta al usuario qué hizo en la última hora (time_range).
    """
    name = user_state.get("name", "Desconocido")
    tr = global_state.get("time_range", {})
    start = tr.get("start_time", "hace 1 hora")
    end = tr.get("end_time", "ahora")

    prompt = (
        "Eres Zendell, un sistema multiagente amigable. El usuario dijo:\n"
        f"'{last_message}'\n\n"
        f"Sabes que su nombre es {name}. Quieres saber qué hizo entre {start} y {end}. "
        "Genera una respuesta en español, invitando al usuario a describir sus actividades de la última hora."
    )
    return prompt

def build_prompt_ask_next_hour(last_message: str, user_state: dict, global_state: dict) -> str:
    """
    Pregunta al usuario qué planea hacer en la próxima hora (time_range).
    """
    name = user_state.get("name", "Desconocido")
    tr = global_state.get("time_range", {})
    start = tr.get("start_time", "ahora")
    end = tr.get("end_time", "en 1 hora")

    prompt = (
        "Eres Zendell, un sistema multiagente en español. El usuario describió su última hora:\n"
        f"'{last_message}'\n\n"
        f"Ahora pregúntale qué planea hacer entre {start} y {end}. "
        "Hazlo de forma amistosa y enfocada a entender sus planes."
    )
    return prompt

def build_prompt_final(last_message: str, user_state: dict) -> str:
    prompt = (
        "Eres Zendell, un sistema multiagente. El usuario acaba de decir:\n"
        f"'{last_message}'\n\n"
        "Ya registraste sus actividades pasadas y futuras. "
        "Genera una respuesta breve, ofreciéndote a dar recomendaciones o despedirte "
        "hasta la siguiente interacción."
    )
    return prompt
