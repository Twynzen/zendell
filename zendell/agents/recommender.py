# zendell/agents/recommender.py

from typing import Dict, Any
from datetime import datetime
from zendell.services.llm_provider import ask_gpt
from zendell.core.db import MongoDBManager

def recommender_node(global_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    1. Toma el 'analysis' desde global_state["analysis"].
    2. Usa GPT para generar recomendaciones basadas en ese analysis.
    3. Guarda dichas recomendaciones en DB como 'assistant' y las añade a global_state["recommendation"].
    """
    user_id = global_state.get("user_id", "unknown_user")
    analysis_info = global_state.get("analysis", {})
    summary_text = analysis_info.get("summary", "")

    # Si no tenemos un resumen de análisis, retornamos algo genérico
    if not summary_text:
        global_state["recommendation"] = ["No hay análisis disponible, no se pueden generar recomendaciones."]
        return global_state

    # Preparamos un prompt con la info del análisis
    prompt = (
        f"Basado en este análisis: '{summary_text}', "
        f"genera 2-3 recomendaciones prácticas y breves "
        f"para que el usuario mejore su día."
    )

    recommendations_text = ask_gpt(prompt)
    if not recommendations_text:
        recommendations_text = "No se pudieron obtener recomendaciones."

    # Convertimos las líneas de texto en una lista
    # Podrías parsear con \n
    rec_list = [line.strip() for line in recommendations_text.split("\n") if line.strip()]

    # Guardamos la lista en el global_state
    global_state["recommendation"] = rec_list

    # Registramos en DB que el 'assistant' está sugiriendo algo
    db_manager = MongoDBManager()
    db_manager.save_conversation_message(
        user_id=user_id,
        role="assistant",
        content="\n".join(rec_list),
        extra_data={"step": "recommender_node"}
    )

    # (Opcional) Actualizamos user_state con un "últimas recomendaciones"
    current_state = db_manager.get_state(user_id)
    # Podrías almacenar en short_term_info o un campo nuevo
    if len(rec_list) > 0:
        current_state["short_term_info"].append(f"Recommender => {rec_list[0]}")
    db_manager.save_state(user_id, current_state)

    return global_state
