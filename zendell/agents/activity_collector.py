# zendell/agents/activity_collector.py

from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime
from zendell.services.llm_provider import ask_gpt
from zendell.core.db import MongoDBManager

# Podrías definir un State TypedDict si gustas, 
# pero usaré un dict generico para la interfaz con langgraph.
# El 'global_state' vendrá con user_id, etc.

def activity_collector_node(global_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    1. Recibe el 'global_state' con la info del usuario y el último mensaje (si aplica).
    2. Llama a LLM para clasificar la actividad/mensaje en una categoría.
    3. Almacena la actividad en DB y retorna un 'global_state' actualizado.
    """
    user_id = global_state.get("user_id", "unknown_user")
    last_message = global_state.get("last_message", "")
    if not last_message:
        # Si no hay mensaje que procesar, devolvemos el state tal cual
        return global_state

    # Instanciamos el DBManager (en un proyecto real, se inyecta o se maneja de otro modo)
    db_manager = MongoDBManager()

    # Guardar el mensaje del usuario en la DB como nuevo "mensaje" en conversation_logs
    db_manager.save_conversation_message(
        user_id=user_id,
        role="user",
        content=last_message,
        extra_data={"step": "activity_collector"}  # Puedes añadir más metadatos
    )

    # Usamos GPT para clasificar la actividad
    prompt = (
        f"Clasifica el siguiente texto en una de estas categorías: "
        f"['Trabajo','Descanso','Ejercicio','Ocio','Otro'].\n"
        f"Texto: '{last_message}'\n"
        f"Responde solo con la categoría."
    )
    activity_type = ask_gpt(prompt)
    if not activity_type:
        activity_type = "Otro"

    # Insertar la actividad en la DB
    activity_data = {
        "activity": last_message,
        "type": activity_type
    }
    db_manager.add_activity(user_id, activity_data)

    # Actualizar el estado local (en RAM) 
    # - Se asume que 'activities' es un list[dict]
    if "activities" not in global_state:
        global_state["activities"] = []
    global_state["activities"].append(activity_data)

    # Devolvemos el global_state
    return global_state
