# /agents/goal_finder.py

from typing import TypedDict, Optional, List
from datetime import datetime
from services.llm_provider import ask_gpt

class State(TypedDict):
    customer_name: Optional[str]  # Nombre del usuario, puede ser None si es la primera vez
    general_info: dict            # Información general a largo plazo (nombre, sueños, hobbies, etc.)
    short_term_info: List[str]    # Actividades o metas a corto plazo
    last_interaction_time: str    # Tiempo de la última interacción con el usuario

def goal_finder_node(state: State) -> State:
    """
    Nodo que contacta al usuario, busca objetivos y actualiza el estado.
    Genera dinámicamente el prompt para el LLM en función del contexto actual del usuario.
    """

    # Verificamos si es la primera interacción
    if not state.get("customer_name"):
        # Si es la primera vez, pedimos al LLM que genere un mensaje para recopilar información general
        context_prompt = (
            "Es la primera vez que interactúas con este usuario. Necesitas conocer información general "
            "sobre él, como su nombre, a qué se dedica, cuáles son sus sueños, gustos y hobbies. "
            "Genera un mensaje amigable y no invasivo para iniciar la conversación."
        )
    else:
        # Si ya hay información del usuario, pedimos al LLM que genere un mensaje adecuado
        # basado en sus actividades recientes y su estado general
        recent_activities = ", ".join(
            [activity for activity in state["short_term_info"][-3:]]  # Tomamos las últimas 3 actividades
        )
        context_prompt = (
            f"Estás interactuando nuevamente con el usuario '{state['customer_name']}'. "
            f"Las últimas actividades registradas son: {recent_activities}. "
            "Genera un mensaje amigable para preguntarle cómo va su día y si hay algo en lo que puedas ayudarle."
        )

    # Enviamos el contexto al LLM para que genere el mensaje
    response = ask_gpt(context_prompt)

    # Actualizamos el estado según el tipo de interacción
    if not state.get("customer_name"):
        state["general_info"] = {"respuesta_inicial": response}
        state["customer_name"] = "Desconocido"  # Temporal, hasta que obtengamos el nombre real
    else:
        state["short_term_info"].append(response)

    # Actualizamos el tiempo de la última interacción
    state["last_interaction_time"] = datetime.now().isoformat()

    return state
