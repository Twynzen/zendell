# zendell/agents/orchestrator.py
from typing import Dict, Any
from zendell.core.db import MongoDBManager
from zendell.agents.activity_collector import activity_collector_node
from zendell.agents.analyzer import analyzer_node
from zendell.agents.recommender import recommender_node

def orchestrator_flow(user_id: str, last_message: str) -> Dict[str, Any]:
    db_manager = MongoDBManager()
    user_state = db_manager.get_state(user_id)

    # Ver o crear el stage
    conversation_stage = user_state.get("conversation_stage", "initial")

    # 1) Llamamos activity_collector
    global_state = {
        "user_id": user_id,
        "customer_name": user_state.get("name", "Desconocido"),
        "activities": [],
        "analysis": {},
        "recommendation": [],
        "last_message": last_message,
        "conversation_context": []
    }
    global_state = activity_collector_node(global_state)

    # Si se extrajo un name, lo guardamos en user_state
    user_state = db_manager.get_state(user_id)  # Releer la BD tras update
    conversation_stage = user_state.get("conversation_stage", conversation_stage)

    # Decidir próximo paso según stage
    if conversation_stage == "initial":
        # Si ya tenemos un name != "Desconocido", pasamos a "collecting_activities"
        if user_state["name"] != "Desconocido":
            conversation_stage = "collecting_activities"
            # Respuesta para quien nos acaba de dar su nombre:
            final_text = f"¡Mucho gusto, {user_state['name']}! Me alegra conocerte. " \
                         "¿Qué metas tienes a corto plazo o qué proyectos te interesan?"
        else:
            # Todavía no tenemos nombre
            final_text = "¡Gracias por responder! Me gustaría saber tu nombre y ocupación para conocerte mejor."
    elif conversation_stage == "collecting_activities":
        # Aquí si quieres, ya pasas al analyzer o le sigues preguntando
        # por su día, su rutina, etc.
        # O decimos: "¿Qué harás hoy?" y no llamamos el recommender aún
        final_text = "Entendido. Cuéntame un poco sobre tu rutina diaria o lo que planeas hacer hoy."
        # Podrías setear conversation_stage = "ready_to_recommend" si ya quieres recomendar
    else:
        # stage "ready_to_recommend" -> corremos analyzer y recommender
        global_state = analyzer_node(global_state)
        global_state = recommender_node(global_state)
        recs = global_state.get("recommendation", [])
        if recs:
            final_text = "Aquí tienes mis sugerencias:\n" + "\n".join(recs)
        else:
            final_text = "Gracias por la info, por ahora no tengo recomendaciones."

    # Guardamos stage en user_state
    user_state["conversation_stage"] = conversation_stage
    db_manager.save_state(user_id, user_state)

    # Registramos final_text en conversation logs
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
