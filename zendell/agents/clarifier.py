# zendell/agents/clarifier.py

import json
from datetime import datetime
from zendell.services.llm_provider import ask_gpt

def clarifier_node(global_state: dict) -> dict:
    """
    Genera preguntas de clarificación para actividades detectadas.
    
    Este nodo:
    1. Analiza las actividades detectadas por activity_collector_node
    2. Formula preguntas específicas para obtener más información
    3. Almacena estas preguntas en global_state y en la base de datos
    """
    last_msg = global_state.get("last_message", "")
    activities = global_state.get("activities", [])
    db = global_state["db"]
    user_id = global_state.get("user_id", "")
    
    if not last_msg or not activities:
        global_state["clarification_questions"] = []
        return global_state
    
    # Si hay actividades con preguntas de clarificación ya generadas,
    # seleccionar las mejores preguntas para mostrar al usuario
    all_questions = []
    for activity in activities:
        activity_questions = activity.get("clarification_questions", [])
        if activity_questions:
            # Añadir la primera pregunta de cada actividad con contexto
            question_with_context = f"Sobre '{activity['title']}': {activity_questions[0]}"
            all_questions.append({
                "question": question_with_context,
                "activity_id": activity.get("activity_id"),
                "original_question": activity_questions[0]
            })
    
    # Si no hay suficientes preguntas, generar nuevas
    if len(all_questions) < 2:
        # Generar preguntas basadas en todas las actividades
        prompt = (
            f"Analiza el mensaje del usuario: '{last_msg}'. "
            f"Se detectaron estas actividades: {[a['title'] for a in activities]}. "
            "Genera 2-3 preguntas de clarificación relevantes para entender mejor estas actividades. "
            "Las preguntas deben ser específicas, no genéricas, y abordar aspectos como: "
            "contexto, motivación, detalles relevantes, sentimientos o cualquier información que falte. "
            "No preguntes sobre información ya proporcionada. "
            "Devuelve un JSON con este formato: {\"questions\": [\"Pregunta 1\", \"Pregunta 2\"]}"
        )
        
        response = ask_gpt(prompt)
        
        try:
            data = json.loads(response)
            questions = data.get("questions", [])
            
            # Asociar estas preguntas generales con todas las actividades
            for question in questions:
                all_questions.append({
                    "question": question,
                    "activity_id": None,  # No asociada a una actividad específica
                    "original_question": question
                })
        except Exception as e:
            print(f"Error al procesar preguntas de clarificación: {e}")
            # Fallback: una pregunta genérica
            all_questions.append({
                "question": "¿Podrías darme más detalles sobre estas actividades?",
                "activity_id": None,
                "original_question": "¿Podrías darme más detalles sobre estas actividades?"
            })
    
    # Limitar a 3 preguntas máximo
    selected_questions = all_questions[:3]
    
    # Actualizar global_state con las preguntas seleccionadas
    global_state["clarification_questions"] = [q["question"] for q in selected_questions]
    global_state["clarification_metadata"] = selected_questions
    
    # Prompt final después de las preguntas específicas
    final_prompt = "¿Hay algo más que quieras aclarar sobre estas actividades?"
    global_state["clarification_final_prompt"] = final_prompt
    
    # Registrar en la base de datos
    state = db.get_state(user_id)
    state.setdefault("clarifier_history", []).append({
        "timestamp": datetime.utcnow().isoformat(),
        "clarification_questions": [q["question"] for q in selected_questions],
        "activities": [a.get("activity_id") for a in activities],
        "final_prompt": final_prompt
    })
    db.save_state(user_id, state)
    
    return global_state

def process_clarifier_response(global_state: dict) -> dict:
    """
    Procesa la respuesta del usuario a las preguntas de clarificación.
    
    Este nodo:
    1. Analiza la respuesta del usuario a las preguntas de clarificación
    2. Vincula esta respuesta con las actividades correspondientes
    3. Actualiza la base de datos y genera posibles nuevas preguntas
    """
    user_input = global_state.get("user_clarifier_response", global_state.get("last_message", ""))
    activities = global_state.get("activities", [])
    question_metadata = global_state.get("clarification_metadata", [])
    
    if not user_input or not activities:
        return global_state
    
    db = global_state["db"]
    user_id = global_state.get("user_id", "")
    
    # Obtener las preguntas que se hicieron
    questions_asked = [meta["question"] for meta in question_metadata]
    
    # Si no hay preguntas registradas, usar una genérica para el análisis
    if not questions_asked:
        questions_asked = ["Pregunta de clarificación sobre las actividades"]
    
    # Analizar la respuesta del usuario
    prompt = (
        f"El usuario respondió: '{user_input}' a las siguientes preguntas de clarificación: "
        f"{questions_asked}. "
        "Extrae información relevante y estructurada de esta respuesta. "
        "Para cada respuesta, determina:\n"
        "1. Qué información nueva aporta\n"
        "2. Qué detalles específicos proporciona\n"
        "3. Cómo enriquece la comprensión de las actividades\n\n"
        "Devuelve un JSON con este formato:\n"
        '{"analysis": [\n'
        '  {"question": "Pregunta 1", "extracted_info": "Información concisa extraída", "insights": "Observación relevante"},\n'
        '  ...\n'
        '], "new_questions": ["Posible pregunta adicional 1", "Posible pregunta 2"]}'
    )
    
    response = ask_gpt(prompt)
    
    try:
        data = json.loads(response)
        extracted_analyses = data.get("analysis", [])
        new_questions = data.get("new_questions", [])
    except Exception as e:
        print(f"Error al procesar respuesta del clarificador: {e}")
        extracted_analyses = [{
            "question": questions_asked[0] if questions_asked else "Clarificación",
            "extracted_info": user_input,
            "insights": "Información adicional proporcionada por el usuario."
        }]
        new_questions = []
    
    # Actualizar actividades con la información obtenida
    for meta in question_metadata:
        activity_id = meta.get("activity_id")
        if not activity_id:
            continue
        
        # Buscar análisis correspondiente a esta pregunta
        matching_analysis = None
        for analysis in extracted_analyses:
            if analysis["question"] == meta["question"] or analysis["question"] == meta["original_question"]:
                matching_analysis = analysis
                break
        
        if not matching_analysis:
            matching_analysis = {
                "question": meta["question"],
                "extracted_info": user_input,
                "insights": "No se pudo extraer información específica."
            }
        
        # Crear estructura de pregunta-respuesta
        qa_entry = {
            "question": meta["original_question"],
            "answer": user_input,
            "extracted_info": matching_analysis["extracted_info"],
            "insights": matching_analysis["insights"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Actualizar la actividad en la base de datos
        db.add_clarification_to_activity(activity_id, meta["original_question"], user_input)
        
        # Actualizar nuestro global_state
        for i, activity in enumerate(activities):
            if activity.get("activity_id") == activity_id:
                if "clarifier_responses" not in activity:
                    activity["clarifier_responses"] = []
                activity["clarifier_responses"].append(qa_entry)
                global_state["activities"][i] = activity
    
    # Si hay actividades sin asociación específica (preguntas generales)
    general_activities = [a for a in activities if not any(m.get("activity_id") == a.get("activity_id") for m in question_metadata)]
    
    if general_activities and extracted_analyses:
        # Usar el primer análisis para todas las actividades generales
        general_analysis = extracted_analyses[0]
        qa_entry = {
            "question": general_analysis["question"],
            "answer": user_input,
            "extracted_info": general_analysis["extracted_info"],
            "insights": general_analysis["insights"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for activity in general_activities:
            activity_id = activity.get("activity_id")
            if activity_id:
                # Actualizar en la base de datos
                db.add_clarification_to_activity(activity_id, general_analysis["question"], user_input)
    
    # Actualizar el estado del usuario
    state = db.get_state(user_id)
    state.setdefault("clarifier_history", []).append({
        "timestamp": datetime.utcnow().isoformat(),
        "user_response": user_input,
        "structured_analyses": extracted_analyses,
        "new_questions": new_questions
    })
    db.save_state(user_id, state)
    
    # Actualizar global_state con la información procesada
    global_state["clarifier_responses"] = [analysis["extracted_info"] for analysis in extracted_analyses]
    global_state["clarifier_insights"] = [analysis["insights"] for analysis in extracted_analyses]
    global_state["new_clarification_questions"] = new_questions
    
    # Realizar análisis general de la respuesta para extraer entidades y conceptos importantes
    analyze_response_for_insights(global_state, user_input)
    
    return global_state

def analyze_response_for_insights(global_state: dict, user_input: str) -> None:
    """
    Analiza la respuesta del usuario para extraer entidades y conceptos importantes.
    Actualiza el perfil del usuario con esta información.
    """
    db = global_state["db"]
    user_id = global_state.get("user_id", "")
    
    # Extraer entidades y conceptos
    db._extract_entities_from_message(user_id, user_input)
    
    # Extraer información personal
    db.extract_and_update_user_info(user_id, user_input)