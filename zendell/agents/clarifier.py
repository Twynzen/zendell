# zendell/agents/clarifier.py

from zendell.services.llm_provider import ask_gpt
import json

def clarifier_node(global_state: dict) -> dict:
    last_msg = global_state.get("last_message", "")
    activities = global_state.get("activities", [])
    prompt = f"El usuario escribió: '{last_msg}'. Se registraron las siguientes actividades: {activities}. Si hay ambigüedad en alguna de estas actividades, genera preguntas de clarificación específicas, por ejemplo, sobre el objetivo, la periodicidad o detalles relevantes. Devuelve una lista en formato JSON con la clave 'questions'."
    response = ask_gpt(prompt)
    try:
        data = json.loads(response)
        questions = data.get("questions", [])
    except:
        questions = []
    global_state["clarification_questions"] = questions
    return global_state
