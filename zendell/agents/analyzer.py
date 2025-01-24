# zendell/agents/analyzer.py

from typing import Dict, Any
from collections import Counter
from zendell.services.llm_provider import ask_gpt
from zendell.core.db import MongoDBManager

def analyzer_node(global_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    1. Lee las actividades (global_state["activities"]) y genera un análisis con GPT.
    2. Guarda el resultado en la DB (user_state y/o conversation_logs).
    3. Devuelve un 'analysis' en global_state["analysis"] para el siguiente nodo.
    """
    user_id = global_state.get("user_id", "unknown_user")
    activities = global_state.get("activities", [])
    
    # Si no hay actividades, no hay mucho que analizar
    if not activities:
        global_state["analysis"] = {
            "summary": "No hay actividades registradas para analizar.",
            "tone": "N/A"
        }
        return global_state

    # Ejemplo: Contar la frecuencia de cada tipo de actividad
    activity_types = [act["type"] for act in activities]
    type_counts = Counter(activity_types)

    # Construimos un prompt para GPT
    prompt = (
        f"El usuario ha registrado las siguientes actividades con la frecuencia: {dict(type_counts)}.\n"
        f"Analiza cómo podría equilibrar mejor su tiempo y describe su posible estado emocional."
    )

    analysis_text = ask_gpt(prompt)
    if not analysis_text:
        analysis_text = "No se pudo obtener un análisis del LLM."

    # Almacenamos el análisis en el global_state
    global_state["analysis"] = {
        "summary": analysis_text,
        "tone": "indeterminado"  # Podrías parsear si GPT dice "está estresado" u otro
    }

    # Opcional: Guardar en DB - se puede meter en conversation_logs como un "mensaje del sistema"
    db_manager = MongoDBManager()
    db_manager.save_conversation_message(
        user_id=user_id,
        role="system",
        content=analysis_text,
        extra_data={"step": "analyzer_node"}
    )

    # También podrías guardar en user_state si deseas tenerlo persistente:
    current_state = db_manager.get_state(user_id)
    # Ejemplo: guardamos en "short_term_info" un resumen
    current_state["short_term_info"].append(f"Analysis result: {analysis_text[:100]}...")
    db_manager.save_state(user_id, current_state)

    return global_state
