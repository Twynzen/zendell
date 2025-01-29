# zendell/agents/orchestrator.py

from typing import Dict, Any
from zendell.agents.goal_finder import goal_finder_node
from zendell.agents.activity_collector import activity_collector_node
from zendell.agents.analyzer import analyzer_node
from zendell.agents.recommender import recommender_node
from zendell.core.db import MongoDBManager

# Fijamos un ID único porque es un sistema para un solo usuario
SINGLE_USER_ID = "my_unique_user"

def initiate_conversation() -> str:
    """
    Llamado cuando el sistema decide iniciar (de forma proactiva)
    la conversación con el usuario. Retorna el mensaje que se debe enviar.
    """
    db_manager = MongoDBManager()
    # Llamamos al goal_finder_node que determina si procede o no
    # iniciar la conversación y genera el mensaje inicial
    final_state = goal_finder_node(SINGLE_USER_ID)

    # goal_finder_node retorna el estado, donde típicamente hemos guardado
    # la respuesta en conversation_logs. Para obtener el mensaje:
    last_assistant_msg = db_manager.get_last_assistant_message(SINGLE_USER_ID)

    if last_assistant_msg:
        return last_assistant_msg
    else:
        return "Error: No se generó un mensaje de inicio."


def process_user_response(user_message: str) -> str:
    """
    Llamado cuando el usuario contesta. Orquesta el pipeline:
    1) activity_collector -> 2) analyzer -> 3) recommender
    Retorna el mensaje final (ej. las recomendaciones).
    """
    db_manager = MongoDBManager()

    # Construimos un 'global_state' básico
    global_state = {
        "user_id": SINGLE_USER_ID,
        "last_message": user_message,
        "activities": [],
        "analysis": {},
        "recommendation": []
    }

    # 1) activity_collector
    global_state = activity_collector_node(global_state)

    # 2) analyzer
    global_state = analyzer_node(global_state)

    # 3) recommender
    global_state = recommender_node(global_state)

    # Podríamos unificar las recomendaciones en un texto final
    rec_list = global_state.get("recommendation", [])
    if rec_list:
        final_text = "Aquí tienes algunas recomendaciones:\n" + "\n".join(rec_list)
    else:
        final_text = "¡Gracias por la info! Por ahora no tengo recomendaciones."

    # Guardamos ese final_text en conversation_logs (opcional)
    db_manager.save_conversation_message(
        user_id=SINGLE_USER_ID,
        role="assistant",
        content=final_text,
        extra_data={"step": "orchestrator_flow"}
    )

    return final_text
