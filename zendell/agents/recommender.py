# zendell/agents/recommender.py

from typing import Dict, Any
from datetime import datetime
from zendell.services.llm_provider import ask_gpt

def recommender_node(global_state: Dict[str, Any]) -> Dict[str, Any]:
    user_id = global_state.get("user_id", "unknown_user")
    analysis_info = global_state.get("analysis", {})
    summary_text = analysis_info.get("summary", "")
    if not summary_text:
        global_state["recommendation"] = ["No hay análisis disponible, no se pueden generar recomendaciones."]
        return global_state
    prompt = (
        f"Basado en este análisis: '{summary_text}', genera 2-3 recomendaciones prácticas y breves para que el usuario mejore su día."
    )
    recommendations_text = ask_gpt(prompt)
    if not recommendations_text:
        recommendations_text = "No se pudieron obtener recomendaciones."
    rec_list = [line.strip() for line in recommendations_text.split("\n") if line.strip()]
    global_state["recommendation"] = rec_list
    db = global_state["db"]
    db.save_conversation_message(user_id=user_id, role="assistant", content="\n".join(rec_list), extra_data={"step": "recommender_node"})
    current_state = db.get_state(user_id)
    if rec_list:
        current_state["short_term_info"].append(f"Recommender => {rec_list[0]}")
    db.save_state(user_id, current_state)
    return global_state