from typing import TypedDict, Optional, List
from datetime import datetime, timedelta, date
from services.llm_provider import ask_gpt

# ==============================================================================
#                               STATE DEFINITION
# ==============================================================================
class State(TypedDict):
    customer_name: Optional[str]        # Nombre del usuario, None si es la primera vez
    general_info: dict                  # Info general: {'nombre': str, 'ocupacion': str, 'suenios': str, ...}
    short_term_info: List[str]          # Metas o actividades a corto plazo
    last_interaction_time: str          # Última vez que se interactuó con el usuario (ISO8601)
    daily_interaction_count: int        # Cantidad de interacciones en el día actual
    last_interaction_date: str          # Fecha (YYYY-MM-DD) de la última interacción

# ==============================================================================
#                      HELPER: VERIFICAR SI PODEMOS INTERACTUAR
# ==============================================================================
def can_interact(last_time_str: str, hours: int = 1) -> bool:
    """
    Devuelve True si han pasado 'hours' horas desde 'last_time_str'.
    Si 'last_time_str' está vacío o con formato inválido, retornamos True por defecto.
    """
    if not last_time_str:
        return True

    try:
        last_time = datetime.fromisoformat(last_time_str)
    except ValueError:
        return True  # si el formato es inválido, interactuamos

    return (datetime.now() - last_time) >= timedelta(hours=hours)

# Opcional: para ignorar 8 horas de sueño,
# podríamos hacer una verificación del current_hour local del usuario.
# EJEMPLO TEÓRICO (no implementado):
def is_within_active_hours(now: datetime) -> bool:
    # Suponiendo que usuario duerme de 23:00 a 07:00
    # Ajusta a tu preferencia
    if now.hour >= 23 or now.hour < 7:
        return False
    return True

# ==============================================================================
#                             MAIN GOAL FINDER NODE
# ==============================================================================
def goal_finder_node(
    user_id: str,
    db_manager,  # Objeto hipotético que maneja la lectura/escritura en la BD
    hours_between_interactions: int = 1,
    max_daily_interactions: int = 16
) -> State:
    """
    1. Carga (o crea) el estado del usuario desde la BD.
    2. Verifica si ya pasó el tiempo necesario (hours_between_interactions).
    3. Revisa si ya llegamos a 'max_daily_interactions' o si estamos en horas de sueño.
    4. Si es primera interacción, genera un prompt amigable para recopilar datos generales.
    5. Si no, genera un prompt personalizado con la info previa.
    6. Llama al LLM (ask_gpt) y actualiza el 'State'.
    7. Guarda el estado en la BD.
    8. Retorna el 'State' final.
    """

    # ==========================================================================
    # 1. Intentamos leer el estado del usuario desde la BD.
    # ==========================================================================
    try:
        state: State = db_manager.get_state(user_id)
    except Exception as e:
        print(f"[GoalFinder] Error leyendo la BD: {e}")
        # Si falla, creamos un estado "nuevo".
        state = {
            "customer_name": None,
            "general_info": {},
            "short_term_info": [],
            "last_interaction_time": "",
            "daily_interaction_count": 0,
            "last_interaction_date": ""
        }

    # ==========================================================================
    # Preparaciones
    # ==========================================================================
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    # Si cambió el día, reseteamos el contador diario
    if state.get("last_interaction_date", "") != today_str:
        state["daily_interaction_count"] = 0
        state["last_interaction_date"] = today_str

    # ==========================================================================
    # 2. Verificamos si podemos iniciar (horas entre interacciones).
    # ==========================================================================
    if not can_interact(state.get("last_interaction_time", ""), hours_between_interactions):
        print("[GoalFinder] Todavía no es hora de otra interacción (intervalo).")
        return state

    # ==========================================================================
    # 3. Revisamos si estamos en horas activas y si no hemos superado el límite diario
    # ==========================================================================
    # EJEMPLO: si quisiéramos forzar las horas activas
    # if not is_within_active_hours(now):
    #     print("[GoalFinder] Usuario está en horas de sueño. No interactuamos.")
    #     return state

    if state["daily_interaction_count"] >= max_daily_interactions:
        print("[GoalFinder] Se alcanzó el límite diario de interacciones. No interactuamos más hoy.")
        return state

    # ==========================================================================
    # 4. Preparamos el prompt. ¿Primera vez?
    # ==========================================================================
    if not state.get("customer_name"):
        context_prompt = (
            "Es tu primer encuentro con este usuario. Necesitas saber su nombre, ocupación, sueños y gustos principales. "
            "Crea un mensaje amigable, breve y no invasivo para que el usuario se sienta en confianza. "
            "Incluye preguntas esenciales para personalizar tu asistencia."
        )
    else:
        # Tomamos las últimas 3 actividades registradas (si existen)
        recent_activities = ", ".join(state["short_term_info"][-3:]) if state["short_term_info"] else "Ninguna"
        context_prompt = (
            f"Estás interactuando nuevamente con '{state['customer_name']}'. "
            f"Las últimas metas/actividades registradas: {recent_activities}. "
            "Genera un mensaje cordial para saludar, preguntar cómo va su día y "
            "averiguar si hay nuevas metas o necesidades. Considera que queremos "
            "saber qué hizo en la última hora y qué planea para la siguiente."
        )

    # ==========================================================================
    # 5. Llamamos al LLM para obtener el mensaje que se le presentará al usuario.
    # ==========================================================================
    llm_response = ask_gpt(context_prompt)

    # ==========================================================================
    # 6. Actualizamos el estado con la nueva info
    # ==========================================================================
    if not state["customer_name"]:
        state["customer_name"] = "Desconocido"
        state["general_info"]["respuesta_inicial"] = llm_response
    else:
        state["short_term_info"].append(llm_response)

    # Registramos la hora actual y aumentamos el contador diario
    state["last_interaction_time"] = now.isoformat()
    state["daily_interaction_count"] += 1
    state["last_interaction_date"] = today_str

    # ==========================================================================
    # 7. Guardamos el estado actualizado en la BD.
    # ==========================================================================
    try:
        db_manager.save_state(user_id, state)
    except Exception as e:
        print(f"[GoalFinder] Error guardando en la BD: {e}")
        # Se podría decidir si hacemos rollback o no.

    return state
