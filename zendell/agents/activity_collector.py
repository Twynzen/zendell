# zendell/agents/activity_collector.py

import json
import re
from datetime import datetime
from zendell.services.llm_provider import ask_gpt
from bson.objectid import ObjectId

def activity_collector_node(global_state: dict) -> dict:
    """
    Recolecta actividades del usuario a partir de su mensaje.
    
    Este agente se encarga de:
    1. Extraer información de perfil durante las etapas initial/ask_profile
    2. Extraer actividades durante ask_last_hour y ask_next_hour
    3. Generar preguntas de clarificación sobre esas actividades
    4. Razonar sobre las actividades detectadas
    """
    user_id = global_state.get("user_id", "")
    last_msg = global_state.get("last_message", "")
    db = global_state["db"]
    
    if not last_msg:
        return global_state
    
    # Obtener el estado actual del usuario
    st = db.get_state(user_id)
    
    # Si estamos en etapas iniciales, extraer información para el perfil
    if st.get("conversation_stage", "initial") in ["initial", "ask_profile"]:
        # Extraer y actualizar la información del perfil
        extracted_info = db.extract_and_update_user_info(user_id, last_msg)
        
        # Registrar el mensaje del usuario en el contexto a corto plazo
        db.add_to_short_term_info(user_id, f"[User] {last_msg}")
        
        # En estas etapas, no recolectamos actividades
        return global_state
    
    # Guardar mensaje en contexto de corto plazo
    db.add_to_short_term_info(user_id, f"[User] {last_msg}")
    
    # Solo recolectar actividades durante etapas específicas
    stage = st.get("conversation_stage", "initial")
    if stage not in ["ask_last_hour", "ask_next_hour"]:
        return global_state
    
    # Determinar el contexto temporal (pasado o futuro)
    time_context = "future" if stage == "ask_next_hour" else "past"
    
    # Clasificar la categoría de la actividad
    category = classify_activity(last_msg)
    
    # Extraer subactividades del mensaje
    sub_activities = extract_sub_activities(last_msg, time_context)
    
    # Si no se detectaron subactividades, crear una por defecto
    if not sub_activities:
        filtered_msg = re.split(r'\?', last_msg)[-1].strip() or last_msg
        default_title = " ".join(filtered_msg.split()[:5]) if filtered_msg.split() else "Actividad"
        default_activity = {
            "title": default_title,
            "category": category,
            "time_context": time_context
        }
        sub_activities = [default_activity]
    
    # Procesar cada actividad detectada
    new_activities = []
    for sub in sub_activities:
        # Crear el objeto de actividad
        activity_id = str(ObjectId())
        
        activity_data = {
            "activity_id": activity_id,
            "title": sub.get("title", "Sin título"),
            "category": sub.get("category", category),
            "time_context": sub.get("time_context", time_context),
            "timestamp": datetime.utcnow().isoformat(),
            "original_message": last_msg,
            "clarification_questions": [],
            "clarifier_responses": [],
            "completed": False,
            "importance": sub.get("importance", 5)
        }
        
        # Generar preguntas de clarificación específicas para esta actividad
        activity_data["clarification_questions"] = generate_clarification_questions(last_msg, activity_data["title"])
        
        # Extraer entidades mencionadas en relación con esta actividad
        entities = extract_entities_from_activity(last_msg, activity_data["title"])
        activity_data["entities"] = entities
        
        # Añadir análisis inicial de la actividad
        activity_data["analysis"] = analyze_activity(activity_data["title"], last_msg, time_context)
        
        # Guardar la actividad en la base de datos
        db.add_activity(user_id, activity_data)
        
        # Guardar mensaje de sistema sobre la actividad detectada
        db.save_conversation_message(
            user_id,
            "system", 
            f"Actividad detectada: {activity_data['title']} (Categoría: {activity_data['category']})",
            {"step": "activity_collector"}
        )
        
        # Añadir la actividad procesada a la lista
        new_activities.append(activity_data)
    
    # Generar razonamiento sobre todas las actividades detectadas
    reasoning_prompt = (
        f"El mensaje '{last_msg}' generó las siguientes actividades: "
        f"{[act['title'] for act in new_activities]}. "
        f"Explica por qué se detectaron estas actividades específicas y qué elementos permitieron identificarlas. "
        f"Analiza también qué podrían indicar estas actividades sobre los intereses, prioridades o "
        f"estado actual del usuario. Elabora un razonamiento detallado pero conciso."
    )
    
    reasoning = ask_gpt(reasoning_prompt)
    
    # Guardar el razonamiento en el estado del usuario
    interaction_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "activities": [{"id": act["activity_id"], "title": act["title"]} for act in new_activities],
        "reasoning": reasoning
    }
    
    # Actualizar el estado con las nuevas actividades y el razonamiento
    st.setdefault("interaction_history", []).append(interaction_entry)
    
    # Actualizar específicamente las listas de actividades según el contexto temporal
    if time_context == "past":
        st.setdefault("activities_last_hour", []).append(interaction_entry)
    else:
        st.setdefault("activities_next_hour", []).append(interaction_entry)
    
    # Guardar el estado actualizado
    db.save_state(user_id, st)
    
    # Actualizar el estado global para el orquestador
    global_state["activities"].extend(new_activities)
    global_state["activity_reasoning"] = reasoning
    
    return global_state

def classify_activity(msg: str) -> str:
    """Clasifica el tipo de actividad basado en el mensaje del usuario."""
    print(f"[COLLECTOR] Clasificando actividad del mensaje: '{msg[:50]}...'")
    
    prompt = (
        f"Analiza el siguiente mensaje: '{msg}'. Determina la categoría más adecuada para la actividad descrita. "
        "Elige entre estas categorías: Trabajo, Estudio, Ocio, Ejercicio, Social, Alimentación, Descanso, "
        "Transporte, Cuidado Personal, Tareas Domésticas, o Otra. "
        "Devuelve únicamente un JSON válido con este formato: {\"category\": \"Categoría elegida\"}"
    )
    
    response = ask_gpt(prompt)
    print(f"[COLLECTOR] Respuesta de clasificación: '{response[:100]}...'")
    
    try:
        import json
        import re
        
        # Buscar patrón JSON en la respuesta
        json_pattern = r'(\{.*\})'
        matches = re.search(json_pattern, response, re.DOTALL)
        
        if matches:
            json_str = matches.group(1)
            data = json.loads(json_str)
        else:
            # Intentar limpiar y parsear
            cleaned_response = re.sub(r'^[^{]*', '', response)
            cleaned_response = re.sub(r'[^}]*$', '', cleaned_response)
            
            if cleaned_response:
                data = json.loads(cleaned_response)
            else:
                print("[COLLECTOR] No se pudo extraer JSON de la clasificación, usando categoría por defecto")
                return "Otra"
        
        category = data.get("category", "Otra")
        print(f"[COLLECTOR] Categoría detectada: {category}")
        return category.strip()
    except Exception as e:
        print(f"[COLLECTOR] Error al procesar la categoría: {e}")
        return "Otra"

def extract_sub_activities(msg: str, time_context: str) -> list:
    """Extrae diferentes actividades de un mensaje del usuario."""
    print(f"[COLLECTOR] Extrayendo subactividades del mensaje: '{msg[:50]}...'")
    
    prompt = (
        f"Analiza el siguiente mensaje: '{msg}'. Extrae todas las actividades distintas que se describen en el mensaje. "
        f"Cada actividad ocurre en contexto temporal '{time_context}' (past=pasado, future=futuro). "
        "Para cada actividad, extrae:\n"
        "1. Un título descriptivo y conciso\n"
        "2. Una categoría relevante (Trabajo, Estudio, Ocio, Ejercicio, Social, etc.)\n"
        "3. Un nivel de importancia (1-10)\n\n"
        "Devuelve únicamente un JSON con este formato:\n"
        '{"activities": [\n'
        '  {"title": "Título de la actividad", "category": "Categoría", "importance": 5, "time_context": "past"},\n'
        '  {...}\n'
        ']}'
    )
    
    response = ask_gpt(prompt)
    print(f"[COLLECTOR] Respuesta de extracción de subactividades: '{response[:100]}...'")
    
    try:
        import json
        import re
        
        # Limpiar la respuesta y buscar patrón JSON
        cleaned_response = re.sub(r'```json|```', '', response).strip()
        json_pattern = r'(\{.*\})'
        matches = re.search(json_pattern, cleaned_response, re.DOTALL)
        
        if matches:
            json_str = matches.group(1)
            data = json.loads(json_str)
        else:
            # Intentar limpiar y parsear
            cleaned_response = re.sub(r'^[^{]*', '', cleaned_response)
            cleaned_response = re.sub(r'[^}]*$', '', cleaned_response)
            
            if cleaned_response:
                data = json.loads(cleaned_response)
            else:
                print("[COLLECTOR] No se pudo extraer JSON de subactividades, devolviendo lista vacía")
                return []
        
        activities = data.get("activities", [])
        print(f"[COLLECTOR] Se detectaron {len(activities)} subactividades")
        
        # Validar y normalizar cada actividad
        for activity in activities:
            if "title" not in activity or not activity["title"]:
                activity["title"] = "Actividad sin título"
            
            if "category" not in activity or not activity["category"]:
                activity["category"] = "Otra"
            
            if "importance" not in activity or not isinstance(activity["importance"], int):
                activity["importance"] = 5
            
            activity["time_context"] = time_context
        
        return activities
    except Exception as e:
        print(f"[COLLECTOR] Error al extraer subactividades: {e}")
        return []

def generate_clarification_questions(msg: str, activity_title: str) -> list:
    """Genera preguntas de clarificación específicas para una actividad."""
    print(f"[COLLECTOR] Generando preguntas de clarificación para: '{activity_title}'")
    
    prompt = (
        f"Analiza el mensaje: '{msg}'. Considera la actividad '{activity_title}' y genera "
        "preguntas de clarificación específicas y relevantes para obtener más detalles. "
        "Las preguntas deben abordar aspectos como quién, qué, cuándo, dónde, cómo y por qué. "
        "No preguntes por información que ya se menciona claramente en el mensaje. "
        "Devuelve hasta 3 preguntas en formato JSON: {\"questions\": [\"Pregunta 1\", \"Pregunta 2\", ...]}"
    )
    
    response = ask_gpt(prompt)
    print(f"[COLLECTOR] Respuesta de generación de preguntas: '{response[:100]}...'")
    
    try:
        import json
        import re
        
        # Buscar patrón JSON en la respuesta
        json_pattern = r'(\{.*\})'
        matches = re.search(json_pattern, response, re.DOTALL)
        
        if matches:
            json_str = matches.group(1)
            data = json.loads(json_str)
        else:
            # Intentar limpiar y parsear
            cleaned_response = re.sub(r'^[^{]*', '', response)
            cleaned_response = re.sub(r'[^}]*$', '', cleaned_response)
            
            if cleaned_response:
                data = json.loads(cleaned_response)
            else:
                print("[COLLECTOR] No se pudo extraer JSON de preguntas, usando pregunta por defecto")
                return [f"¿Podrías darnos más detalles sobre '{activity_title}'?"]
        
        questions = data.get("questions", [])
        
        # Si hay preguntas, limitar a 3 máximo
        if questions:
            print(f"[COLLECTOR] Se generaron {len(questions)} preguntas de clarificación")
            return questions[:3]
        else:
            # Si no hay preguntas, usar pregunta por defecto
            print("[COLLECTOR] No se generaron preguntas, usando pregunta por defecto")
            return [f"¿Podrías darnos más detalles sobre '{activity_title}'?"]
            
    except Exception as e:
        print(f"[COLLECTOR] Error al generar preguntas de clarificación: {e}")
        # Si hay un error, proporcionar una pregunta genérica
        return [f"¿Podrías darnos más detalles sobre '{activity_title}'?"]

def extract_entities_from_activity(msg: str, activity_title: str) -> list:
    """Extrae entidades (personas, lugares, conceptos) relacionadas con una actividad."""
    print(f"[COLLECTOR] Extrayendo entidades para actividad: '{activity_title}'")
    
    prompt = (
        f"Del mensaje: '{msg}', extrae entidades relacionadas con la actividad '{activity_title}'. "
        "Identifica personas, lugares u organizaciones mencionadas. "
        "Para cada entidad, determina su tipo (person, place, organization, concept) "
        "y su relación con la actividad. "
        "Devuelve un JSON con formato:\n"
        '{"entities": [\n'
        '  {"entity_id": "", "name": "Juan", "type": "person", "relationship": "amigo que acompaña"},\n'
        '  {"entity_id": "", "name": "Parque Central", "type": "place", "relationship": "lugar visitado"}\n'
        ']}'
    )
    
    response = ask_gpt(prompt)
    print(f"[COLLECTOR] Respuesta de extracción de entidades: '{response[:100]}...'")
    
    try:
        import json
        import re
        
        # Buscar patrón JSON en la respuesta
        json_pattern = r'(\{.*\})'
        matches = re.search(json_pattern, response, re.DOTALL)
        
        if matches:
            json_str = matches.group(1)
            data = json.loads(json_str)
        else:
            # Intentar limpiar y parsear
            cleaned_response = re.sub(r'^[^{]*', '', response)
            cleaned_response = re.sub(r'[^}]*$', '', cleaned_response)
            
            if cleaned_response:
                data = json.loads(cleaned_response)
            else:
                print("[COLLECTOR] No se pudo extraer JSON de entidades, devolviendo lista vacía")
                return []
        
        entities = data.get("entities", [])
        
        # Asignar IDs a las entidades
        for entity in entities:
            entity["entity_id"] = str(ObjectId())
        
        print(f"[COLLECTOR] Se detectaron {len(entities)} entidades")
        return entities
    except Exception as e:
        print(f"[COLLECTOR] Error al extraer entidades de actividad: {e}")
        return []
    
def analyze_activity(activity_title: str, full_message: str, time_context: str) -> str:
    """Genera un análisis sobre una actividad específica."""
    context_label = "pasada" if time_context == "past" else "futura"
    
    prompt = (
        f"Analiza la actividad '{activity_title}' mencionada en el mensaje: '{full_message}'. "
        f"Esta es una actividad {context_label} del usuario. "
        "Proporciona un breve análisis (3-5 frases) que incluya:\n"
        "1. Posible motivación para esta actividad\n"
        "2. Qué podría indicar sobre los intereses o prioridades del usuario\n"
        "3. Posible impacto en su bienestar o estado mental\n"
        "Mantén el análisis objetivo y basado en lo mencionado."
    )
    
    analysis = ask_gpt(prompt)
    return analysis