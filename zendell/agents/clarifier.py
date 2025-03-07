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
    
    print(f"[CLARIFIER] Iniciando clarifier_node con {len(activities)} actividades")
    
    if not last_msg or not activities:
        print("[CLARIFIER] No hay mensaje o actividades, terminando sin preguntas")
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
    
    print(f"[CLARIFIER] Preguntas extraídas de actividades: {len(all_questions)}")
    
    # Si no hay suficientes preguntas, generar nuevas
    if len(all_questions) < 2:
        print("[CLARIFIER] Generando nuevas preguntas de clarificación")
        # Generar preguntas basadas en todas las actividades
        prompt = (
            f"Analiza el mensaje del usuario: '{last_msg}'. "
            f"Se detectaron estas actividades: {[a.get('title', 'Actividad sin título') for a in activities]}. "
            "Genera 2-3 preguntas de clarificación relevantes para entender mejor estas actividades. "
            "Las preguntas deben ser específicas, no genéricas, y abordar aspectos como: "
            "contexto, motivación, detalles relevantes, sentimientos o cualquier información que falte. "
            "No preguntes sobre información ya proporcionada. "
            "Devuelve SOLO un JSON con este formato (nada de texto adicional): {\"questions\": [\"Pregunta 1\", \"Pregunta 2\"]}"
        )
        
        response = ask_gpt(prompt)
        print(f"[CLARIFIER] Respuesta del LLM: '{response[:100]}...'")
        
        try:
            # Intentar limpiar y extraer el JSON con regex
            import re
            import json
            
            # Buscar patrón JSON en la respuesta
            json_pattern = r'(\{.*\})'
            matches = re.search(json_pattern, response, re.DOTALL)
            
            if matches:
                json_str = matches.group(1)
                print(f"[CLARIFIER] JSON extraído: '{json_str[:50]}...'")
                data = json.loads(json_str)
            else:
                # Intentar limpiar eliminando texto antes y después de llaves
                cleaned_response = re.sub(r'^[^{]*', '', response)
                cleaned_response = re.sub(r'[^}]*$', '', cleaned_response)
                print(f"[CLARIFIER] Respuesta limpiada: '{cleaned_response[:50]}...'")
                
                if cleaned_response:
                    data = json.loads(cleaned_response)
                else:
                    print("[CLARIFIER] No se pudo extraer JSON, usando pregunta por defecto")
                    raise ValueError("No JSON found")
            
            questions = data.get("questions", [])
            
            # Asociar estas preguntas generales con todas las actividades
            for question in questions:
                all_questions.append({
                    "question": question,
                    "activity_id": None,  # No asociada a una actividad específica
                    "original_question": question
                })
                
            print(f"[CLARIFIER] {len(questions)} preguntas generadas")
                
        except Exception as e:
            print(f"[CLARIFIER] Error al procesar preguntas de clarificación: {e}")
            # Fallback: una pregunta genérica
            fallback_question = "¿Podrías darme más detalles sobre estas actividades?"
            all_questions.append({
                "question": fallback_question,
                "activity_id": None,
                "original_question": fallback_question
            })
            print("[CLARIFIER] Usando pregunta fallback")
    
    # Limitar a 3 preguntas máximo
    selected_questions = all_questions[:3]
    print(f"[CLARIFIER] Preguntas seleccionadas finales: {len(selected_questions)}")
    
    # Actualizar global_state con las preguntas seleccionadas
    global_state["clarification_questions"] = [q["question"] for q in selected_questions]
    global_state["clarification_metadata"] = selected_questions
    
    # Prompt final después de las preguntas específicas
    final_prompt = "¿Hay algo más que quieras aclarar sobre estas actividades?"
    global_state["clarification_final_prompt"] = final_prompt
    
    # Registrar en la base de datos
    try:
        state = db.get_state(user_id)
        state.setdefault("clarifier_history", []).append({
            "timestamp": datetime.utcnow().isoformat(),
            "clarification_questions": [q["question"] for q in selected_questions],
            "activities": [a.get("activity_id", "") for a in activities if a.get("activity_id")],
            "final_prompt": final_prompt
        })
        db.save_state(user_id, state)
    except Exception as e:
        print(f"[CLARIFIER] Error al guardar historial de clarificación: {e}")
    
    print("[CLARIFIER] clarifier_node completado con éxito")
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
    
    print(f"[CLARIFIER] Procesando respuesta del usuario: '{user_input[:50]}...'")
    
    if not user_input or not activities:
        print("[CLARIFIER] No hay input de usuario o actividades para procesar")
        return global_state
    
    db = global_state["db"]
    user_id = global_state.get("user_id", "")
    
    # Obtener las preguntas que se hicieron
    questions_asked = [meta.get("question", "") for meta in question_metadata if meta.get("question")]
    
    # Si no hay preguntas registradas, usar una genérica para el análisis
    if not questions_asked:
        print("[CLARIFIER] No hay preguntas registradas, usando genérica")
        questions_asked = ["Pregunta de clarificación sobre las actividades"]
    
    print(f"[CLARIFIER] Preguntas realizadas: {questions_asked}")
    
    # Analizar la respuesta del usuario
    prompt = (
        f"El usuario respondió: '{user_input}' a las siguientes preguntas de clarificación: "
        f"{questions_asked}. "
        "Extrae información relevante y estructurada de esta respuesta. "
        "Para cada respuesta, determina:\n"
        "1. Qué información nueva aporta\n"
        "2. Qué detalles específicos proporciona\n"
        "3. Cómo enriquece la comprensión de las actividades\n\n"
        "Devuelve un JSON con este formato (y SOLO este formato, sin texto adicional):\n"
        '{"analysis": [\n'
        '  {"question": "Pregunta 1", "extracted_info": "Información concisa extraída", "insights": "Observación relevante"},\n'
        '  ...\n'
        '], "new_questions": ["Posible pregunta adicional 1", "Posible pregunta 2"]}'
    )
    
    response = ask_gpt(prompt)
    print(f"[CLARIFIER] Respuesta del LLM: '{response[:100]}...'")
    
    # Preparar análisis por defecto
    default_analysis = {
        "question": questions_asked[0] if questions_asked else "Clarificación",
        "extracted_info": user_input,
        "insights": "Información adicional proporcionada por el usuario."
    }
    
    try:
        # Intentar limpiar y extraer el JSON con regex
        import re
        import json
        
        # Buscar patrón JSON en la respuesta
        json_pattern = r'(\{.*\})'
        matches = re.search(json_pattern, response, re.DOTALL)
        
        if matches:
            json_str = matches.group(1)
            print(f"[CLARIFIER] JSON extraído: '{json_str[:50]}...'")
            data = json.loads(json_str)
        else:
            # Intentar limpiar eliminando texto antes y después de llaves
            cleaned_response = re.sub(r'^[^{]*', '', response)
            cleaned_response = re.sub(r'[^}]*$', '', cleaned_response)
            print(f"[CLARIFIER] Respuesta limpiada: '{cleaned_response[:50]}...'")
            
            if cleaned_response:
                data = json.loads(cleaned_response)
            else:
                print("[CLARIFIER] No se pudo extraer JSON, usando análisis por defecto")
                raise ValueError("No JSON found")
        
        extracted_analyses = data.get("analysis", [])
        new_questions = data.get("new_questions", [])
        
        # Verificar que haya análisis
        if not extracted_analyses:
            print("[CLARIFIER] Análisis vacío, usando análisis por defecto")
            extracted_analyses = [default_analysis]
            
    except Exception as e:
        print(f"[CLARIFIER] Error al procesar respuesta del clarificador: {e}")
        # Valores por defecto
        extracted_analyses = [default_analysis]
        new_questions = []
    
    # Asegurar que tenemos al menos un análisis
    if not extracted_analyses:
        extracted_analyses = [default_analysis]
    
    print(f"[CLARIFIER] Análisis extraídos: {len(extracted_analyses)}")
    
    # Actualizar actividades con la información obtenida
    updated_activities = 0
    
    for meta in question_metadata:
        activity_id = meta.get("activity_id")
        if not activity_id:
            continue
        
        # Buscar análisis correspondiente a esta pregunta
        matching_analysis = None
        for analysis in extracted_analyses:
            question = analysis.get("question", "")
            if question and (question == meta.get("question", "") or question == meta.get("original_question", "")):
                matching_analysis = analysis
                break
        
        if not matching_analysis:
            matching_analysis = {
                "question": meta.get("question", "Pregunta no identificada"),
                "extracted_info": user_input,
                "insights": "No se pudo extraer información específica."
            }
        
        # Crear estructura de pregunta-respuesta
        qa_entry = {
            "question": meta.get("original_question", "Pregunta no identificada"),
            "answer": user_input,
            "extracted_info": matching_analysis.get("extracted_info", user_input),
            "insights": matching_analysis.get("insights", "No se generaron insights."),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Actualizar la actividad en la base de datos
            db.add_clarification_to_activity(activity_id, qa_entry["question"], user_input)
            updated_activities += 1
            
            # Actualizar nuestro global_state
            for i, activity in enumerate(activities):
                if activity.get("activity_id") == activity_id:
                    if "clarifier_responses" not in activity:
                        activity["clarifier_responses"] = []
                    activity["clarifier_responses"].append(qa_entry)
                    global_state["activities"][i] = activity
        except Exception as e:
            print(f"[CLARIFIER] Error al actualizar actividad {activity_id}: {e}")
    
    print(f"[CLARIFIER] Actividades actualizadas: {updated_activities}")
    
    # Si hay actividades sin asociación específica (preguntas generales)
    general_activities = [a for a in activities if not any(m.get("activity_id") == a.get("activity_id") for m in question_metadata)]
    
    if general_activities and extracted_analyses:
        # Usar el primer análisis para todas las actividades generales
        general_analysis = extracted_analyses[0]
        qa_entry = {
            "question": general_analysis.get("question", "Pregunta general"),
            "answer": user_input,
            "extracted_info": general_analysis.get("extracted_info", user_input),
            "insights": general_analysis.get("insights", "No se generaron insights."),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for activity in general_activities:
            activity_id = activity.get("activity_id")
            if activity_id:
                try:
                    # Actualizar en la base de datos
                    db.add_clarification_to_activity(activity_id, qa_entry["question"], user_input)
                except Exception as e:
                    print(f"[CLARIFIER] Error al actualizar actividad general {activity_id}: {e}")
    
    # Actualizar el estado del usuario
    try:
        state = db.get_state(user_id)
        state.setdefault("clarifier_history", []).append({
            "timestamp": datetime.utcnow().isoformat(),
            "user_response": user_input,
            "structured_analyses": extracted_analyses,
            "new_questions": new_questions if isinstance(new_questions, list) else []
        })
        db.save_state(user_id, state)
    except Exception as e:
        print(f"[CLARIFIER] Error al actualizar estado del usuario: {e}")
    
    # Actualizar global_state con la información procesada
    global_state["clarifier_responses"] = [analysis.get("extracted_info", "") for analysis in extracted_analyses]
    global_state["clarifier_insights"] = [analysis.get("insights", "") for analysis in extracted_analyses]
    global_state["new_clarification_questions"] = new_questions if isinstance(new_questions, list) else []
    
    # Realizar análisis general de la respuesta para extraer entidades y conceptos importantes
    try:
        analyze_response_for_insights(global_state, user_input)
    except Exception as e:
        print(f"[CLARIFIER] Error al analizar insights: {e}")
    
    print("[CLARIFIER] Procesamiento de respuesta completado")
    return global_state

def analyze_response_for_insights(global_state: dict, user_input: str) -> None:
    """
    Analiza la respuesta del usuario para extraer entidades y conceptos importantes.
    Actualiza el perfil del usuario con esta información.
    """
    db = global_state["db"]
    user_id = global_state.get("user_id", "")
    
    print(f"[CLARIFIER] Analizando respuesta para insights: '{user_input[:50]}...'")
    
    try:
        # Extraer entidades y conceptos
        entities = db._extract_entities_from_message(user_id, user_input)
        print(f"[CLARIFIER] Entidades extraídas: {len(entities)}")
    except Exception as e:
        print(f"[CLARIFIER] Error al extraer entidades: {e}")
    
    try:
        # Extraer información personal
        info = db.extract_and_update_user_info(user_id, user_input)
        print(f"[CLARIFIER] Información personal extraída: {len(info) if info else 0} campos")
    except Exception as e:
        print(f"[CLARIFIER] Error al extraer información personal: {e}")