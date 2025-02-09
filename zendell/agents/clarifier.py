# zendell/agents/clarifier.py

from zendell.services.llm_provider import ask_gpt
import json

def clarifier_node(global_state: dict) -> dict:
    last_msg = global_state.get("last_message", "")
    activities = global_state.get("activities", [])
    prompt = (
        f"El usuario escribió: '{last_msg}'. Se registraron las siguientes actividades: {activities}. "
        "Analiza si hay ambigüedad en términos de contexto, intención, duración, lugar o detalles específicos en cada actividad. "
        "Genera preguntas de clarificación precisas para obtener más información sobre cada una de ellas. "
        "Devuelve la lista de preguntas en formato JSON con la clave 'questions'."
    )
    response = ask_gpt(prompt)
    try:
        data = json.loads(response)
        questions = data.get("questions", [])
    except:
        questions = []
    global_state["clarification_questions"] = questions
    return global_state
