# /agents/activity_collector.py

from typing import TypedDict, Optional, List, Dict
from services.llm_provider import ask_gpt
from datetime import datetime


class State(TypedDict):
    customer_name: str
    activities: List[Dict[str, str]]
    last_activity_time: str
    connected_channel: str  # ID o nombre del canal donde se envió la comunicación.
    last_connection_info: str  # Podría ser un timestamp con info del canal


def activity_collector_node(
    state: dict,  # Usamos dict para ser flexible con los campos
    new_activity: Optional[str] = None,
    channel_info: Optional[str] = None  # Nuevo parámetro opcional para el canal
) -> dict:
    if "activities" not in state or state["activities"] is None:
        state["activities"] = []

    if new_activity:
        prompt = f"Clasifica la siguiente actividad en una de estas categorías: Trabajo, Descanso, Ejercicio, Ocio, Otro. Actividad: '{new_activity}'. Responde solo con la categoría."
        activity_type = ask_gpt(prompt)
        state["activities"].append({"activity": new_activity, "type": activity_type})

    state["last_activity_time"] = datetime.now().isoformat()
    
    if channel_info:
        state["connected_channel"] = channel_info
        state["last_connection_info"] = f"Conexión registrada a las {state['last_activity_time']} en {channel_info}"

    return state

