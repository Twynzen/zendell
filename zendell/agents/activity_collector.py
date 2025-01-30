from typing import Dict, Any
from datetime import datetime
from zendell.services.llm_provider import ask_gpt
from zendell.core.db import MongoDBManager
import json

def activity_collector_node(global_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    1. Toma el último mensaje del user (last_message).
    2. Clasifica si es una actividad y, si lo es, guarda en 'activities'.
    3. Extrae datos de perfil (nombre, ocupacion, gustos, metas) con LLM y actualiza user_state.
    4. Agrega el mensaje del usuario a short_term_info (si lo consideras necesario).
    5. Retorna el global_state.
    """

    user_id = global_state.get("user_id", "unknown_user")
    last_message = global_state.get("last_message", "")
    if not last_message:
        return global_state

    db_manager = MongoDBManager()

    # -------------------------------------------------------------------------
    # PARTE A: Clasificar actividad
    # -------------------------------------------------------------------------
    classify_prompt = f"""
El usuario dice: "{last_message}"
¿Esto describe una actividad concreta (sí o no)?
Si es sí, clasifícala en estas categorías: [Trabajo, Descanso, Ejercicio, Ocio, Otro].
Devuelve exactamente un valor de esta lista o la palabra "NoActivity" si no describe actividad.
"""
    classification = ask_gpt(classify_prompt) or "NoActivity"
    classification = classification.strip()

    print("[activity_collector] GPT classification raw:", classification)

    valid_categories = ["Trabajo","Descanso","Ejercicio","Ocio","Otro"]
    if classification not in valid_categories:
        classification = "NoActivity"

    if classification != "NoActivity":
        activity_data = {
            "activity": last_message,
            "type": classification
        }
        # db_manager.add_activity(user_id, activity_data)  # Descomenta si quieres guardar en 'activities' collection
        if "activities" not in global_state:
            global_state["activities"] = []
        global_state["activities"].append(activity_data)

    # -------------------------------------------------------------------------
    # PARTE B: Extraer datos de perfil
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
    print("[activity_collector] GPT extract response raw:", extract_response)

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

    print("[activity_collector] extracted JSON:", extracted)

    current_state = db_manager.get_state(user_id)

    # Actualizamos name si lo encontró
    if extracted.get("name"):
        current_state["name"] = extracted["name"]

    # Asegurar 'general_info' existe
    if "general_info" not in current_state:
        current_state["general_info"] = {}

    current_state["general_info"]["ocupacion"] = (
        extracted.get("ocupacion") or current_state["general_info"].get("ocupacion", "")
    )
    current_state["general_info"]["gustos"] = (
        extracted.get("gustos") or current_state["general_info"].get("gustos", "")
    )
    current_state["general_info"]["metas"] = (
        extracted.get("metas") or current_state["general_info"].get("metas", "")
    )

    # -------------------------------------------------------------------------
    # PARTE C: Agregar mensaje del usuario a short_term_info
    # -------------------------------------------------------------------------
    if "short_term_info" not in current_state:
        current_state["short_term_info"] = []
    current_state["short_term_info"].append(f"[UserSaid] {last_message}")

    # Guardar el user_state final en la BD
    db_manager.save_state(user_id, current_state)

    return global_state
