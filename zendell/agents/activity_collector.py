# zendell/agents/activity_collector.py
from typing import Dict, Any
from datetime import datetime
from zendell.services.llm_provider import ask_gpt
from zendell.core.db import MongoDBManager
import json

def activity_collector_node(global_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    1. Toma el último mensaje del user (last_message).
    2. Clasifica si describe una actividad (o varias).
    3. Si es activity, guarda en 'activities' (o en la colección "activities").
    4. Extrae datos de perfil (nombre, ocupacion, gustos, metas) con LLM y actualiza user_state.
    5. Agrega el mensaje a short_term_info.
    6. Retorna global_state.
    """

    user_id = global_state.get("user_id", "unknown_user")
    last_message = global_state.get("last_message", "")
    if not last_message:
        return global_state

    db_manager = MongoDBManager()

    # 1. Extraer datos de perfil (por si menciona nombre, etc.)
    extracted_profile = extract_profile_info(last_message)
    current_state = db_manager.get_state(user_id)

    # Actualizar campos de perfil si se encuentra algo
    if extracted_profile["name"]:
        current_state["name"] = extracted_profile["name"]
    if "general_info" not in current_state:
        current_state["general_info"] = {}
    gen_info = current_state["general_info"]
    gen_info["ocupacion"] = extracted_profile["ocupacion"] or gen_info.get("ocupacion","")
    gen_info["gustos"]    = extracted_profile["gustos"]     or gen_info.get("gustos","")
    gen_info["metas"]     = extracted_profile["metas"]      or gen_info.get("metas","")

    # 2. Reconocer si hay actividades (podríamos tener un time_context)
    classification = classify_activity(last_message)
    time_context = global_state.get("time_context", None)
    time_range = global_state.get("time_range", {})

    # 3. Si classification != "NoActivity", hacemos un segundo prompt
    #    para extraer "sub-actividades" en formato JSON (title, category, time_context).
    if classification != "NoActivity" or time_context in ("last_hour","next_hour"):
        # Extraer sub-actividades
        sub_activities = extract_sub_activities(last_message, time_context)
        # Guardarlas en DB
        for act in sub_activities:
            # Si no hay "start_time"/"end_time" en act, usamos time_range
            act_data = {
                "user_id": user_id,
                "title": act.get("title",""),
                "category": act.get("category",""),
                "time_context": act.get("time_context", "past" if time_context=="last_hour" else "future"),
                "start_time": time_range.get("start_time",""),
                "end_time": time_range.get("end_time",""),
                "original_message": last_message,
                "timestamp": datetime.utcnow().isoformat()
            }
            db_manager.add_activity(user_id, act_data)  # Necesitas implementar o descomentar en db.py
            # De manera opcional, si quieres guardarlo también en global_state["activities"]:
            if "activities" not in global_state:
                global_state["activities"] = []
            global_state["activities"].append(act_data)

    # 4. Guardar short_term_info
    if "short_term_info" not in current_state:
        current_state["short_term_info"] = []
    current_state["short_term_info"].append(f"[UserSaid] {last_message}")

    # 5. Guardar el user_state final en la BD
    db_manager.save_state(user_id, current_state)

    return global_state

# ----------------------------------
# Funciones auxiliares
# ----------------------------------

def extract_profile_info(message: str) -> dict:
    """
    Llama a GPT y extrae name, ocupacion, gustos, metas en formato JSON.
    """
    prompt = f"""
El usuario dice: "{message}"
Extrae los siguientes datos en formato JSON:
{{
  "name": "",
  "ocupacion": "",
  "gustos": "",
  "metas": ""
}}
Si no menciona algo, deja ese campo como string vacío.
"""
    response = ask_gpt(prompt)
    extracted = {
        "name": "",
        "ocupacion": "",
        "gustos": "",
        "metas": ""
    }
    if response:
        # remover backticks
        response = response.replace("```json","").replace("```","").strip()
        try:
            data = json.loads(response)
            for k in extracted.keys():
                extracted[k] = data.get(k, "")
        except json.JSONDecodeError:
            pass
    return extracted

def classify_activity(message: str) -> str:
    """
    Pregunta a GPT si describe una actividad concreta.
    Retorna: "Trabajo","Descanso","Ejercicio","Ocio","Otro" o "NoActivity".
    """
    prompt = f"""
El usuario dice: "{message}"
¿Esto describe una actividad concreta (sí o no)?
Si es sí, clasifícala en estas categorías: [Trabajo, Descanso, Ejercicio, Ocio, Otro].
Devuelve exactamente un valor de esta lista o "NoActivity".
"""
    classification = ask_gpt(prompt) or "NoActivity"
    classification = classification.strip()
    valid = ["Trabajo","Descanso","Ejercicio","Ocio","Otro"]
    if classification not in valid:
        classification = "NoActivity"
    return classification

def extract_sub_activities(message: str, time_context: str) -> list:
    """
    Segundo prompt para GPT.
    Queremos un JSON con "activities": [ { "title": "", "category": "", "time_context": "past"|"future" } ]
    Si no encuentra nada, activities=[]
    """
    # pasamos la palabra "past" o "future" según time_context
    default_ctxt = "past" if time_context=="last_hour" else "future" if time_context=="next_hour" else "unknown"

    prompt = f"""
El usuario dice: "{message}"
Asumiendo que se refiere a actividades realizadas si es "last_hour", o planeadas si es "next_hour".
Crea un JSON con la estructura:
{{
  "activities": [
    {{
      "title": "",
      "category": "",
      "time_context": "{default_ctxt}"
    }}
  ]
}}
Enumera cada actividad distinta que mencione. Usa "category" para algo como "Doméstico", "Estudio", "Trabajo", "Ejercicio", etc.
Si no encuentras actividades, pon "activities": [].
"""
    response = ask_gpt(prompt)
    activities_list = []

    if response:
        resp_clean = response.replace("```json","").replace("```","").strip()
        try:
            data = json.loads(resp_clean)
            activities_list = data.get("activities", [])
        except json.JSONDecodeError:
            pass

    return activities_list
