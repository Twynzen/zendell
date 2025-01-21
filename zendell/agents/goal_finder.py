# agents/goal_finder.py
from datetime import datetime, timedelta
from services.llm_provider import ask_gpt

def can_interact(last_time_str: str, hours: int = 1) -> bool:
    if not last_time_str:
        return True
    try:
        last_time = datetime.fromisoformat(last_time_str)
    except ValueError:
        return True
    return (datetime.now() - last_time) >= timedelta(hours=hours)

def goal_finder_node(user_id: str, db_manager, hours_between_interactions: int = 1, max_daily_interactions: int = 16):
    # 1. Intentar leer el estado de la BD
    try:
        state = db_manager.get_state(user_id)
    except Exception as e:
        print(f"[GoalFinder] Error leyendo la BD: {e}")
        state = {
            "customer_name": None,
            "general_info": {},
            "short_term_info": [],
            "last_interaction_time": "",
            "daily_interaction_count": 0,
            "last_interaction_date": ""
        }
        print("[GoalFinder] La base de datos no responde. Continuando con estado temporal.")
        # Guardar estado localmente
        try:
            import json
            with open(f"{user_id}_state.json", "w") as f:
                json.dump(state, f)
            print(f"[GoalFinder] Estado temporal guardado localmente en {user_id}_state.json.")
        except Exception as save_error:
            print(f"[GoalFinder] Error al guardar estado local: {save_error}")

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    if state.get("last_interaction_date", "") != today_str:
        state["daily_interaction_count"] = 0
        state["last_interaction_date"] = today_str

    if not can_interact(state.get("last_interaction_time", ""), hours_between_interactions):
        print("[GoalFinder] No ha pasado el tiempo entre interacciones.")
        return state

    if state["daily_interaction_count"] >= max_daily_interactions:
        print("[GoalFinder] Se ha alcanzado el límite diario de interacciones.")
        return state

    # 4. Preparar el prompt
    if not state.get("customer_name"):
        context_prompt = (
            "Primera vez con este usuario. Necesitas saber su nombre, ocupación, sueños y gustos. "
            "Genera un mensaje cordial que lo invite a presentarse, debes también presentarte y debes recordar que eres un sistema multiagente llamado Zendell."
        )
    else:
        recent_activities = ", ".join(state["short_term_info"][-3:]) if state["short_term_info"] else "Ninguna"
        context_prompt = (
            f"Ya interactuaste con este usuario. Información previa: {recent_activities}. "
            "Genera un saludo y pregunta por nuevas metas."
        )

    llm_response = ask_gpt(context_prompt)
    if not state.get("customer_name"):
        state["customer_name"] = "Desconocido"
        state["general_info"]["respuesta_inicial"] = llm_response
    else:
        state["short_term_info"].append(llm_response)

    state["last_interaction_time"] = now.isoformat()
    state["daily_interaction_count"] += 1
    state["last_interaction_date"] = today_str

    try:
        db_manager.save_state(user_id, state)
    except Exception as e:
        print(f"[GoalFinder] Error guardando en la BD: {e}")
    return state
