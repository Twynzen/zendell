# /agents/analyzer.py

from typing import TypedDict, List, Dict
from services.llm_provider import ask_gpt
from collections import Counter

class State(TypedDict):
    customer_name: str
    activities: List[Dict[str, str]]  # Lista de actividades con tipo {'activity': str, 'type': str}
    analysis: str

def analyzer_node(state: State) -> State:
    """
    Analiza la lista de actividades y genera un análisis basado en patrones de frecuencia y tipo.
    """

    if not state["activities"]:
        state["analysis"] = "No hay actividades registradas para analizar."
        return state

    # Contamos la frecuencia de cada tipo de actividad
    activity_types = [activity["type"] for activity in state["activities"]]
    type_counts = Counter(activity_types)

    # Preparamos un prompt para el LLM con los patrones de actividad detectados
    prompt = f"El usuario ha registrado actividades con la siguiente frecuencia: {dict(type_counts)}. Genera un análisis breve que sugiera cómo podría equilibrar mejor su tiempo."

    # Llamamos al LLM para obtener un análisis basado en los patrones detectados
    analysis = ask_gpt(prompt)
    state["analysis"] = analysis

    return state
