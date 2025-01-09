# /agents/activity_collector.py

from typing import TypedDict, Optional, List, Dict
from services.llm_provider import ask_gpt

class State(TypedDict):
    customer_name: str
    activities: List[Dict[str, str]]  # Lista de actividades con tipo {'activity': str, 'type': str}
    last_activity_time: str

def activity_collector_node(
    state: State,
    new_activity: Optional[str] = None
) -> State:
    """
    Recolecta la actividad (si viene), la categoriza usando un LLM y la registra en el estado.
    """

    if "activities" not in state or state["activities"] is None:
        state["activities"] = []

    if new_activity:
        # Preparamos un prompt para el LLM para categorizar la actividad
        prompt = f"Clasifica la siguiente actividad en una de estas categorías: Trabajo, Descanso, Ejercicio, Ocio, Otro. Actividad: '{new_activity}'. Responde solo con la categoría."
        activity_type = ask_gpt(prompt)

        # Añadimos la actividad con su categoría al estado
        state["activities"].append({"activity": new_activity, "type": activity_type})

    # Registramos la hora de la última actividad
    from datetime import datetime
    state["last_activity_time"] = datetime.now().isoformat()

    return state
