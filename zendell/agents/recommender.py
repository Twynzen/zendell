# /agents/recommender.py

from typing import TypedDict, List, Dict
from datetime import datetime
from services.llm_provider import ask_gpt

class State(TypedDict):
    customer_name: str
    activities: List[Dict[str, str]]
    analysis: str
    recommendation: List[str]
    last_recommendation_time: str

def recommender_node(state: State) -> State:
    """
    Genera recomendaciones basadas en el análisis y el contexto horario.
    """

    if not state["analysis"]:
        state["recommendation"] = ["No hay análisis disponible para generar recomendaciones."]
        return state

    # Determinamos la hora actual
    current_hour = datetime.now().hour

    # Preparamos un prompt considerando el análisis y la hora actual
    prompt = f"El usuario tiene el siguiente análisis: '{state['analysis']}'. La hora actual es {current_hour}:00. Genera tres recomendaciones adecuadas para este momento del día."

    # Llamamos al LLM para obtener recomendaciones
    recommendations_text = ask_gpt(prompt)
    recommendations = recommendations_text.split("\n")[:3]

    state["recommendation"] = recommendations
    state["last_recommendation_time"] = datetime.now().isoformat()

    return state
