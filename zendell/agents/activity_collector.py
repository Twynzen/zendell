# zendell/agents/activity_collector.py

from typing import Dict, Any
from datetime import datetime
from zendell.services.llm_provider import ask_gpt
from zendell.core.db import MongoDBManager
import json

def activity_collector_node(global_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    1. Revisa el 'last_message' del usuario para ver si describe una actividad.
       - Si SÍ, la clasifica y la guarda en 'activities' (y DB).
       - Si NO, no guarda nada en 'activities'.
    2. Extrae datos de perfil (nombre, ocupacion, gustos, metas) del mensaje
       y los guarda en user_state.general_info.
    3. Retorna el 'global_state' actualizado.
    """

    user_id = global_state.get("user_id", "unknown_user")
    last_message = global_state.get("last_message", "")
    if not last_message:
        # Si no hay mensaje que procesar, devolvemos el state tal cual
        return global_state

    db_manager = MongoDBManager()

    # -------------------------------------------------------------------------
    # PARTE 1: Clasificar si es una actividad real o no
    # -------------------------------------------------------------------------
    classify_prompt = f"""
El usuario dice: "{last_message}"
¿Esto describe una actividad concreta (sí o no)? 
Si es sí, clasifícala en estas categorías: [Trabajo, Descanso, Ejercicio, Ocio, Otro].
Devuelve exactamente un valor de esta lista o la palabra "NoActivity" si no describe actividad.
"""
    classification = ask_gpt(classify_prompt) or "NoActivity"
    classification = classification.strip()

    if classification not in ["Trabajo","Descanso","Ejercicio","Ocio","Otro"]:
        classification = "NoActivity"

    # Si es una actividad, guardarla en DB y en global_state["activities"]
    if classification != "NoActivity":
        activity_data = {
            "activity": last_message,
            "type": classification
        }
        db_manager.add_activity(user_id, activity_data)

        # Actualizar el estado local (en RAM)
        if "activities" not in global_state:
            global_state["activities"] = []
        global_state["activities"].append(activity_data)

    # -------------------------------------------------------------------------
    # PARTE 2: Extraer datos de perfil del mensaje
    # (Nombre, ocupación, gustos, metas) y guardarlos en user_state
    # -------------------------------------------------------------------------
    extract_prompt = f"""
El usuario dice: "{last_message}"
Extrae los siguientes datos en formato JSON:
{{
  "name": "",
  "ocupacion": "",
  "gustos": "",
  "metas": ""
}}
Si no menciona algo, deja ese campo como string vacío.
"""
    extract_response = ask_gpt(extract_prompt)
    if extract_response:
        try:
            extracted = json.loads(extract_response)
        except json.JSONDecodeError:
            extracted = {
                "name": "",
                "ocupacion": "",
                "gustos": "",
                "metas": ""
            }
    else:
        extracted = {
            "name": "",
            "ocupacion": "",
            "gustos": "",
            "metas": ""
        }

    # Cargar el user_state actual
    current_state = db_manager.get_state(user_id)

    # Actualizar 'name' si se menciona
    if extracted.get("name"):
        current_state["name"] = extracted["name"]
    # Actualizar en general_info
    if "general_info" not in current_state:
        current_state["general_info"] = {}

    # Combinar datos de profile
    current_state["general_info"]["ocupacion"] = (
        extracted.get("ocupacion") or current_state["general_info"].get("ocupacion", "")
    )
    current_state["general_info"]["gustos"] = (
        extracted.get("gustos") or current_state["general_info"].get("gustos", "")
    )
    current_state["general_info"]["metas"] = (
        extracted.get("metas") or current_state["general_info"].get("metas", "")
    )

    # Guardamos los cambios en la DB
    db_manager.save_state(user_id, current_state)

    return global_state
