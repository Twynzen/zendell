# zendell/agents/goal_finder.py

from datetime import datetime, timedelta
from zendell.services.llm_provider import ask_gpt

def can_interact(last_time_str: str, hours: int = 1) -> bool:
    if not last_time_str:
        return True
    try:
        last_time = datetime.fromisoformat(last_time_str)
    except ValueError:
        return True
    return (datetime.now() - last_time) >= timedelta(hours=hours)

def goal_finder_node(user_id: str, db_manager, hours_between_interactions: int = 1, max_daily_interactions: int = 16):
    state = db_manager.get_state(user_id)
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    if state.get("last_interaction_date", "") != today_str:
        state["daily_interaction_count"] = 0
        state["last_interaction_date"] = today_str
    if not can_interact(state.get("last_interaction_time", ""), hours_between_interactions):
        print("[GoalFinder] No ha transcurrido el intervalo para interactuar.")
        return state
    if state["daily_interaction_count"] >= max_daily_interactions:
        print("[GoalFinder] Límite de interacciones diarias alcanzado.")
        return state
    if not state.get("name") or state["name"] == "Desconocido":
        context_prompt = (
            "Saluda al usuario de manera amigable y pregunta por su nombre, ocupación, sueños y gustos. "
            "Preséntate como Zendell, un sistema multiagente que lo asistirá día a día."
        )
    else:
        recent_info = ", ".join(state["short_term_info"][-3:]) if state["short_term_info"] else "Ninguna."
        context_prompt = (
            f"Has interactuado con {state.get('name', 'el usuario')} antes. Información previa reciente: {recent_info}. "
            "Genera un saludo y pregúntale por nuevas metas o avances."
        )
    llm_response = ask_gpt(context_prompt)
    if not llm_response:
        llm_response = "Error al generar respuesta inicial."
    state["last_interaction_time"] = now.isoformat()
    state["daily_interaction_count"] += 1
    state["short_term_info"].append(f"[GoalFinderResponse] {llm_response[:80]}")
    db_manager.save_conversation_message(user_id=user_id, role="assistant", content=llm_response, extra_data={"step": "goal_finder_node"})
    db_manager.save_state(user_id, state)
    return state