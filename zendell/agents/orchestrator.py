# zendell/agents/orchestrator.py
from typing import Dict, Any
from zendell.core.db import MongoDBManager
from zendell.agents.activity_collector import activity_collector_node
from zendell.agents.analyzer import analyzer_node
from zendell.agents.recommender import recommender_node

def orchestrator_flow(user_id: str, last_message: str) -> Dict[str, Any]:
    """
    Orquesta todo el pipeline:
      1) activity_collector_node
      2) analyzer_node
      3) recommender_node

    Retorna un dict con:
      {
        "global_state": ...,
        "final_text": ...
      }
    """
    db_manager = MongoDBManager()
    
    # Obtenemos (o creamos) el user_state de la BD
    user_state = db_manager.get_state(user_id)

    # Construimos el global_state, puedes agregar más campos si gustas
    global_state = {
        "user_id": user_id,
        "customer_name": user_state.get("name", "Desconocido"),
        "activities": [],
        "analysis": {},
        "recommendation": [],
        "last_message": last_message,
        "conversation_context": []
    }

    # 1. Recopilamos datos del mensaje del usuario
    global_state = activity_collector_node(global_state)

    # 2. Analizamos las actividades registradas (si las hay)
    global_state = analyzer_node(global_state)

    # 3. Generamos recomendaciones finales
    global_state = recommender_node(global_state)

    # Elaboramos un texto de salida
    recs = global_state.get("recommendation", [])
    if recs:
        final_text = "Aquí tienes algunas recomendaciones:\n" + "\n".join(recs)
    else:
        final_text = "He registrado tu mensaje. ¡Gracias!"

    # Guardamos ese final_text como mensaje de 'assistant'
    db_manager.save_conversation_message(
        user_id=user_id,
        role="assistant",
        content=final_text,
        extra_data={"step": "orchestrator_flow"}
    )

    return {
        "global_state": global_state,
        "final_text": final_text
    }
