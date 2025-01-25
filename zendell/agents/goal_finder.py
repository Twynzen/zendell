# zendell/agents/goal_finder.py

from datetime import datetime, timedelta
from typing import Dict, Any
from zendell.services.llm_provider import ask_gpt
from zendell.core.db import MongoDBManager

def can_interact(last_time_str: str, hours: int = 1) -> bool:
    """
    Evalúa si han pasado 'hours' horas desde last_time_str
    para permitir una nueva interacción.
    """
    if not last_time_str:
        return True
    try:
        last_time = datetime.fromisoformat(last_time_str)
    except ValueError:
        return True

    return (datetime.now() - last_time) >= timedelta(hours=hours)


def goal_finder_node(
    user_id: str,
    hours_between_interactions: int = 1,
    max_daily_interactions: int = 16
) -> Dict[str, Any]:
    """
    1. Revisa si se puede interactuar con el user (tiempo/hora).
    2. Si procede, genera un mensaje inicial o de seguimiento (via LLM).
    3. Actualiza la DB y retorna el estado final del user.
    """
    db_manager = MongoDBManager()

    # 1. Intentar leer el estado de la BD
    try:
        state = db_manager.get_state(user_id)
    except Exception as e:
        print(f"[GoalFinder] Error leyendo la BD: {e}")
        # Creamos un estado temporal localmente
        state = {
            "user_id": user_id,
            "name": "Desconocido",
            "general_info": {},
            "short_term_info": [],
            "last_interaction_time": "",
            "daily_interaction_count": 0,
            "last_interaction_date": ""
        }

    # 2. Control de interacciones diarias
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    if state.get("last_interaction_date", "") != today_str:
        # Reseteamos el contador si es un nuevo día
        state["daily_interaction_count"] = 0
        state["last_interaction_date"] = today_str

    # ¿Ha pasado el tiempo mínimo?
    if not can_interact(state.get("last_interaction_time", ""), hours_between_interactions):
        print("[GoalFinder] No ha transcurrido el intervalo para interactuar.")
        return state

    # ¿Se alcanzó el tope diario?
    if state["daily_interaction_count"] >= max_daily_interactions:
        print("[GoalFinder] Límite de interacciones diarias alcanzado.")
        return state

    # 3. Preparar el prompt para GPT:
    if not state.get("name") or state["name"] == "Desconocido":
        # Es la primera vez o no se conoce el nombre
        context_prompt = (
            "Saluda al usuario de manera amigable y pregunta por su nombre, ocupación, sueños y gustos. "
            "Preséntate como Zendell, un sistema multiagente que lo asistirá día a día."
        )
    else:
        # Ya se conoce algo
        recent_info = ", ".join(state["short_term_info"][-3:]) if state["short_term_info"] else "Ninguna."
        context_prompt = (
            f"Has interactuado con {state.get('name', 'el usuario')} antes. "
            f"Información previa reciente: {recent_info}. "
            "Genera un saludo y pregúntale por nuevas metas o avances."
        )

    llm_response = ask_gpt(context_prompt)
    if not llm_response:
        llm_response = "Error al generar respuesta inicial."

    # 4. Actualizamos el estado en la DB
    state["last_interaction_time"] = now.isoformat()
    state["daily_interaction_count"] += 1
    state["short_term_info"].append(f"[GoalFinderResponse] {llm_response[:80]}")  # Resumen en short_term_info

    # Guardar la respuesta como mensaje de rol=assistant en conversation_logs
    db_manager.save_conversation_message(
        user_id=user_id,
        role="assistant",
        content=llm_response,
        extra_data={"step": "goal_finder_node"}
    )

    # Persistimos el estado final
    db_manager.save_state(user_id, state)
    return state
