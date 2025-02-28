# zendell/agents/analyzer.py

from typing import Dict, Any
from collections import Counter
from zendell.services.llm_provider import ask_gpt

def analyzer_node(global_state: Dict[str, Any]) -> Dict[str, Any]:
    db = global_state["db"]
    user_id = global_state.get("user_id", "unknown_user")
    activities = global_state.get("activities", [])
    if not activities:
        global_state["analysis"] = {"summary": "No hay actividades registradas para analizar.", "tone": "N/A"}
        return global_state
    activity_types = [act.get("type", "") for act in activities]
    type_counts = Counter(activity_types)
    prompt = (
        f"El usuario ha registrado las siguientes actividades con la frecuencia: {dict(type_counts)}.\n"
        f"Analiza cómo podría equilibrar mejor su tiempo y describe su posible estado emocional."
    )
    analysis_text = ask_gpt(prompt)
    if not analysis_text:
        analysis_text = "No se pudo obtener un análisis del LLM."
    global_state["analysis"] = {"summary": analysis_text, "tone": "indeterminado"}
    db.save_conversation_message(user_id, "system", analysis_text, {"step": "analyzer_node"})
    current_state = db.get_state(user_id)
    current_state["short_term_info"].append(f"Analysis result: {analysis_text[:100]}...")
    db.save_state(user_id, current_state)
    return global_state