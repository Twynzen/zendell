# zendell/agents/goal_finder.py

from datetime import datetime, timedelta
from core.utils import get_timestamp
from zendell.services.llm_provider import ask_gpt
from zendell.core.memory_manager import MemoryManager

def can_interact(last_time_str: str, hours: int = 1) -> bool:
    """
    Determina si ha pasado suficiente tiempo desde la última interacción.
    
    Args:
        last_time_str: Timestamp ISO de la última interacción
        hours: Horas mínimas entre interacciones
        
    Returns:
        bool: True si ha pasado suficiente tiempo para interactuar
    """
    if not last_time_str:
        return True
    
    try:
        last_time = datetime.fromisoformat(last_time_str)
    except ValueError:
        return True
    
    return (datetime.now() - last_time) >= timedelta(hours=hours)

def goal_finder_node(user_id: str, db_manager, hours_between_interactions: int = 1, max_daily_interactions: int = 16):
    """
    Decide cuándo iniciar una interacción y qué objetivo tiene.
    
    Este nodo:
    1. Verifica si es tiempo de interactuar basado en interacciones previas
    2. Determina el contexto y objetivo de la interacción
    3. Genera un mensaje inicial apropiado
    4. Actualiza el estado del usuario
    
    Args:
        user_id: ID del usuario
        db_manager: Gestor de base de datos
        hours_between_interactions: Horas mínimas entre interacciones
        max_daily_interactions: Máximo de interacciones por día
        
    Returns:
        dict: Estado actualizado del usuario
    """
    # Inicializar gestor de memoria
    memory_manager = MemoryManager(db_manager)
    
    # Obtener estado actual
    state = db_manager.get_state(user_id)
    
    # Hora y fecha actual
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    
    # Verificar si es un nuevo día
    if state.get("last_interaction_date", "") != today_str:
        state["daily_interaction_count"] = 0
        state["last_interaction_date"] = today_str
    
    # Verificar si puede interactuar
    if not can_interact(state.get("last_interaction_time", ""), hours_between_interactions):
        print(f"{get_timestamp()}","[GoalFinder] No ha transcurrido el intervalo para interactuar.")
        return state
    
    # Verificar límite diario
    if state.get("daily_interaction_count", 0) >= max_daily_interactions:
        print(f"{get_timestamp()}","[GoalFinder] Límite de interacciones diarias alcanzado.")
        return state
    
    # Determinar el objetivo de la interacción
    interaction_goals = determine_interaction_goals(user_id, db_manager, memory_manager, state)
    
    # Generar mensaje inicial basado en el contexto
    message = generate_proactive_message(user_id, db_manager, state, interaction_goals)
    
    # Actualizar estado con la nueva interacción
    state["last_interaction_time"] = now.isoformat()
    state["daily_interaction_count"] = state.get("daily_interaction_count", 0) + 1
    
    # Guardar el mensaje en memoria a corto plazo
    db_manager.add_to_short_term_info(user_id, f"[GoalFinder] {message[:80]}...")
    
    # Guardar mensaje en logs de conversación
    db_manager.save_conversation_message(
        user_id=user_id,
        role="assistant",
        content=message,
        extra_data={"step": "goal_finder_node"}
    )
    
    # Guardar estado actualizado
    db_manager.save_state(user_id, state)
    
    return state

def determine_interaction_goals(user_id: str, db_manager, memory_manager, state: dict) -> dict:
    """
    Determina los objetivos específicos para esta interacción.
    """
    # Si es la primera interacción o faltan datos del perfil
    if not state.get("name") or state.get("name") == "Desconocido":
        # Preparar para la etapa inicial
        return {
            "type": "initial_greeting",
            "missing_profile": True,
            "priority": "get_basic_info",
            "context": "Primer contacto, necesita presentarse y mostrar personalidad amigable"
        }
    
    # Obtener el perfil del usuario
    user_profile = db_manager.get_user_profile(user_id)
    
    # Verificar si hay información pendiente en el perfil
    missing_general_info = []
    for field in ["name", "ocupacion", "gustos", "metas"]:
        if not getattr(user_profile.general_info, field, ""):
            missing_general_info.append(field)
    
    if missing_general_info:
        return {
            "type": "complete_profile",
            "missing_fields": missing_general_info,
            "priority": "get_missing_info",
            "context": f"Completar información de perfil: {', '.join(missing_general_info)}"
        }
    
    # *** NUEVA SECCIÓN ***
    # Verificar si el usuario está en una etapa final (conversación anterior completa)
    last_conversation_stage = state.get("conversation_stage", "initial")
    if last_conversation_stage == "final":
        # Este es un usuario que regresa después de una conversación completa
        return {
            "type": "returning_user",
            "priority": "follow_up",
            "context": "Retomar la conversación con usuario conocido"
        }
    # *** FIN DE NUEVA SECCIÓN ***
    
    # Verificar última actividad para determinar contexto
    recent_activities = db_manager.get_recent_activities(user_id, limit=5)
    
    # Verificar si hay actividades futuras pendientes de seguimiento
    future_activities = [act for act in recent_activities if act.get("time_context") == "future"]
    
    if future_activities:
        return {
            "type": "follow_up",
            "priority": "check_activities",
            "pending_activities": [act.get("title") for act in future_activities],
            "context": "Seguimiento de actividades planificadas anteriormente"
        }
    
    # Si no hay nada específico, interacción normal
    return {
        "type": "regular_check",
        "priority": "routine_update",
        "context": "Interacción rutinaria para mantener contacto y recopilar nueva información"
    }
def generate_proactive_message(user_id: str, db_manager, state: dict, goals: dict) -> str:
    """
    Genera un mensaje proactivo basado en el contexto y los objetivos.
    
    Args:
        user_id: ID del usuario
        db_manager: Gestor de base de datos
        state: Estado actual del usuario
        goals: Objetivos de la interacción
        
    Returns:
        str: Mensaje inicial para el usuario
    """
    interaction_type = goals.get("type", "regular_check")
    
    # Mensaje para primer contacto
    if interaction_type == "initial_greeting":
        prompt = (
            "Saluda al usuario de manera amigable y pregunta por su nombre, ocupación, sueños y gustos. "
            "Preséntate como Zendell, un sistema multiagente que lo asistirá día a día. "
            "Explica brevemente que te conectarás periódicamente para conversar y aprender sobre ellos. "
            "Sé cálido, amigable y genuinamente interesado."
        )
    
    # Mensaje para completar perfil
    elif interaction_type == "complete_profile":
        missing = ", ".join(goals.get("missing_fields", []))
        name = state.get("name", "")
        
        prompt = (
            f"Saluda a {name} de forma personalizada y amistosa. "
            f"Necesitas completar su perfil con la siguiente información: {missing}. "
            f"Pide esta información de manera conversacional, explicando que te ayudará "
            f"a proporcionar un mejor servicio y adaptarte a sus necesidades. "
            f"Evita sonar como un formulario."
        )
    
    # Mensaje para seguimiento de actividades
    elif interaction_type == "follow_up":
        name = state.get("name", "")
        pending = ", ".join(goals.get("pending_activities", [])[:2])
        
        prompt = (
            f"Saluda a {name} de forma personalizada. "
            f"La última vez mencionó que planeaba: {pending}. "
            f"Pregunta de manera amistosa cómo fueron esas actividades y qué está haciendo ahora. "
            f"Muestra genuino interés en su respuesta."
        )
        
    elif interaction_type == "returning_user":
        name = state.get("name", "")
        
        # Obtener actividades recientes para contexto
        recent_activities = db_manager.get_recent_activities(user_id, limit=3)
        activities_context = ""
        if recent_activities:
            activity_titles = [act.get("title", "") for act in recent_activities]
            activities_context = f"En nuestra última conversación, hablamos sobre: {', '.join(activity_titles[:2])}. "
        
        prompt = (
            f"Saluda a {name} como alguien con quien ya has conversado anteriormente. "
            f"{activities_context}"
            f"Pregunta cómo ha ido su día desde vuestra última conversación. "
            f"Muestra familiaridad pero sin asumir detalles que no conoces. "
            f"Haz una referencia natural a la conversación anterior y muestra interés en saber qué ha hecho desde entonces."
        )
    
    # Mensaje para verificación rutinaria
    else:
        name = state.get("name", "")
        recent_info = ", ".join(state.get("short_term_info", [])[-3:]) if state.get("short_term_info") else "Ninguna."
        
        prompt = (
            f"Saluda a {name} de forma natural y personalizada. "
            f"Información reciente: {recent_info}. "
            f"Pregunta por su día de hoy o qué ha estado haciendo recientemente. "
            f"Muestra interés genuino y haz una pregunta específica que invite a compartir."
        )
    
    # Generar el mensaje usando el modelo de lenguaje
    message = ask_gpt(prompt)
    
    if not message:
        # Mensaje de respaldo si falla el modelo
        if interaction_type == "initial_greeting":
            message = "¡Hola! Soy Zendell, tu asistente personal. Me encantaría conocerte mejor. ¿Podrías decirme tu nombre y contarme un poco sobre ti?"
        else:
            name = state.get("name", "")
            message = f"¡Hola {name}! ¿Cómo estás hoy? Me gustaría saber qué has estado haciendo recientemente."
    
    return message