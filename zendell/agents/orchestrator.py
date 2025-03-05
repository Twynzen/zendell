# zendell/agents/orchestrator.py

from typing import Dict, Any
from datetime import datetime, timedelta
from zendell.services.llm_provider import ask_gpt_chat
from zendell.agents.activity_collector import activity_collector_node
from zendell.core.memory_manager import MemoryManager

def orchestrator_flow(user_id: str, last_message: str, db_manager) -> Dict[str, Any]:
    """
    Coordina el flujo completo de la conversación y orquesta los diferentes agentes.
    
    Este es el componente central que:
    1. Mantiene el estado de la conversación
    2. Determina qué agente debe actuar en cada momento
    3. Procesa los resultados de cada agente
    4. Construye el contexto adecuado para las respuestas al usuario
    5. Coordina la transición entre etapas
    """
    print(f"[ORCHESTRATOR] START => user_id={user_id}, last_message='{last_message}'")
    
    # Inicializar el gestor de memoria si está disponible, o None si no lo está
    try:
        from zendell.core.memory_manager import MemoryManager
        memory_manager = MemoryManager(db_manager)
        print("[ORCHESTRATOR] Memory Manager inicializado correctamente")
    except Exception as e:
        print(f"[ORCHESTRATOR] Error al inicializar Memory Manager: {e}")
        memory_manager = None
    
    # Obtener el estado actual del usuario
    try:
        state = db_manager.get_state(user_id)
        
        # Verificar si hay campo general_info, si no existe añadirlo
        if "general_info" not in state:
            state["general_info"] = {}
            db_manager.save_state(user_id, state)
            print("[ORCHESTRATOR] Añadido campo general_info al estado del usuario")
            
        print(f"[ORCHESTRATOR] Estado actual: conversation_stage={state.get('conversation_stage', 'initial')}, name={state.get('name', 'Desconocido')}")
    except Exception as e:
        print(f"[ORCHESTRATOR] Error al obtener estado del usuario: {e}")
        # Estado por defecto si hay error
        state = {
            "user_id": user_id,
            "name": "Desconocido",
            "conversation_stage": "initial",
            "short_term_info": [],
            "general_info": {}
        }
    
    # Verificar si hay un override para la etapa
    stage = state.get("conversation_stage", "initial")
    if state.get("conversation_stage_override"):
        print(f"[ORCHESTRATOR] Detected conversation_stage_override={state['conversation_stage_override']}")
        stage = state["conversation_stage_override"]
        # Limpiar el override una vez usado
        state["conversation_stage_override"] = None
        db_manager.save_state(user_id, state)
    
    # Inicializar el estado global que se pasará entre agentes
    global_state = {
        "user_id": user_id,
        "customer_name": state.get("name", "Desconocido"),
        "activities": [],
        "analysis": {},
        "clarification_questions": [],
        "clarifier_responses": [],
        "last_message": last_message,
        "conversation_context": [],
        "db": db_manager,
        "memory_manager": memory_manager
    }
    
    # 1) Procesar el mensaje con el recolector de actividades
    print(f"[ORCHESTRATOR] activity_collector_node => stage={stage}")
    try:
        global_state = activity_collector_node(global_state)
    except Exception as e:
        print(f"[ORCHESTRATOR] Error en activity_collector_node: {e}")
        # Continuamos con el flujo a pesar del error
    
    # 2) Volver a cargar el estado (pudo cambiar en el collector)
    state = db_manager.get_state(user_id)
    
    # Determinar los campos faltantes en el perfil
    missing_fields = get_missing_profile_fields(state)
    
    # Obtener los rangos de tiempo para referencias
    time_ranges = get_time_ranges()
    
    print(f"[ORCHESTRATOR] missing fields={missing_fields}, time_ranges={time_ranges}, current_stage={stage}")
    
    # Variable para la respuesta final
    reply = ""
    
    # Manejar cada etapa de la conversación
    if stage == "initial":
        if missing_fields:
            # Si faltan campos del perfil, pasar a ask_profile
            stage = "ask_profile"
            reply = generate_profile_request(db_manager, user_id, missing_fields)
        else:
            # Si el perfil está completo, pasar a preguntar por la última hora
            stage = "ask_last_hour"
            reply = generate_last_hour_question(db_manager, user_id, time_ranges)
    
    elif stage == "ask_profile":
        if missing_fields:
            # Aún faltan campos, seguir pidiendo información
            reply = generate_profile_request(db_manager, user_id, missing_fields)
        else:
            # Perfil completo, avanzar a preguntar por la última hora
            stage = "ask_last_hour"
            reply = generate_last_hour_question(db_manager, user_id, time_ranges)
    
    elif stage == "ask_last_hour":
        # Pasar a la etapa de clarificación de actividades pasadas
        stage = "clarifier_last_hour"
        global_state["current_period"] = "past"
        
        # Importar clarifier_node solo cuando se necesita con manejo de errores
        try:
            from zendell.agents.clarifier import clarifier_node
            global_state = clarifier_node(global_state)
            
            questions = global_state.get("clarification_questions", [])
            if questions:
                # Generar mensaje con preguntas de clarificación
                reply = generate_clarification_message(db_manager, user_id, questions, "clarifier_last_hour")
            else:
                # Si no hay preguntas, mensaje genérico y continuar
                reply = "Gracias por compartir lo que hiciste. No necesito más detalles sobre eso."
                stage = "ask_next_hour"  # Avanzar directamente
        except Exception as e:
            print(f"[ORCHESTRATOR] Error en clarifier_node para past: {e}")
            # Mensaje genérico y continuar con el flujo
            reply = "Gracias por compartir lo que hiciste. Pasemos a lo siguiente."
            stage = "ask_next_hour"  # Avanzar directamente
    
    elif stage == "clarifier_last_hour":
        # Procesar la respuesta a las preguntas de clarificación
        try:
            from zendell.agents.clarifier import process_clarifier_response
            global_state["user_clarifier_response"] = last_message
            global_state = process_clarifier_response(global_state)
            
            # Avanzar a preguntar por la próxima hora
            stage = "ask_next_hour"
            reply = generate_next_hour_question(db_manager, user_id, time_ranges)
        except Exception as e:
            print(f"[ORCHESTRATOR] Error en process_clarifier_response para past: {e}")
            # Avanzar al siguiente paso a pesar del error
            stage = "ask_next_hour"
            reply = generate_next_hour_question(db_manager, user_id, time_ranges)
    
    elif stage == "ask_next_hour":
        # Pasar a la etapa de clarificación de actividades futuras
        stage = "clarifier_next_hour"
        global_state["current_period"] = "future"
        
        from zendell.agents.clarifier import clarifier_node
        global_state = clarifier_node(global_state)
        
        questions = global_state.get("clarification_questions", [])
        if questions:
            # Generar mensaje con preguntas de clarificación
            reply = generate_clarification_message(db_manager, user_id, questions, "clarifier_next_hour")
        else:
            # Si no hay preguntas, mensaje genérico y continuar
            reply = "Gracias por compartir tus planes. No necesito más detalles sobre eso."
            stage = "final"  # Avanzar directamente
    
    elif stage == "clarifier_next_hour":
        # Procesar la respuesta a las preguntas de clarificación
        from zendell.agents.clarifier import process_clarifier_response
        global_state["user_clarifier_response"] = last_message
        global_state = process_clarifier_response(global_state)
        
        # Realizar análisis sobre las actividades recopiladas
        from zendell.agents.analyzer import analyzer_node
        global_state = analyzer_node(global_state)
        
        # Generar recomendaciones basadas en el análisis
        from zendell.agents.recommender import recommender_node
        global_state = recommender_node(global_state)
        
        # Avanzar a la etapa final
        stage = "final"
        
        # Generar mensaje final con insights y recomendaciones
        reply = generate_final_message(db_manager, user_id, global_state)
    
    elif stage == "final":
        # Generar una respuesta de cierre y preparar para la próxima interacción
        reply = generate_closing_message(db_manager, user_id)
        
        # Actualizar información a largo plazo
        update_long_term_memory(db_manager, memory_manager, user_id)
        
        # Reiniciar el ciclo para la próxima interacción
        stage = "initial"
    
    else:
        # Etapa desconocida, reiniciar por seguridad
        stage = "initial"
        reply = "Parece que hubo un problema en nuestra conversación. ¿Podemos empezar de nuevo?"
    
    # Actualizar la etapa de conversación en el estado
    state["conversation_stage"] = stage
    db_manager.save_state(user_id, state)
    
    # Guardar la respuesta en los logs de conversación
    db_manager.save_conversation_message(user_id, "assistant", reply, {"step": stage})
    
    print(f"[ORCHESTRATOR] END => new_stage={stage}, reply='{reply[:60]}...'")
    
    # Devolver el resultado del flujo
    return {
        "global_state": global_state,
        "final_text": reply
    }

def get_missing_profile_fields(state: dict) -> list:
    """Determina qué campos del perfil faltan por completar."""
    fields = []
    
    # Verificar nombre
    if state.get("name", "Desconocido") in ["", "Desconocido"]:
        fields.append("nombre")
    
    # Verificar información general
    info = state.get("general_info", {})
    if not info.get("ocupacion", ""):
        fields.append("ocupacion")
    if not info.get("gustos", ""):
        fields.append("gustos")
    if not info.get("metas", ""):
        fields.append("metas")
    
    return fields

def get_time_ranges() -> dict:
    """Obtiene los rangos de tiempo para la última y próxima hora."""
    now = datetime.now()
    return {
        "last_hour": {
            "start": (now - timedelta(hours=1)).strftime("%H:%M"),
            "end": now.strftime("%H:%M")
        },
        "next_hour": {
            "start": now.strftime("%H:%M"),
            "end": (now + timedelta(hours=1)).strftime("%H:%M")
        }
    }

def build_system_context(db, user_id: str, stage: str) -> str:
    """Construye el contexto del sistema para el modelo de lenguaje."""
    state = db.get_state(user_id)
    name = state.get("name", "Desconocido")
    st_info = state.get("short_term_info", [])
    last_notes = ". ".join(st_info[-3:]) if st_info else ""
    
    # Contexto base para cualquier etapa
    context = (
        f"ETAPA: {stage}. Usuario: {name}. Últimas notas: {last_notes}. "
        "Objetivo: Recopilar información y mantener una conversación fluida y natural. "
    )
    
    # Contexto específico para cada etapa
    if stage == "ask_profile":
        context += (
            "En esta etapa, pido datos personales básicos como nombre, ocupación, "
            "gustos y metas de forma amigable y conversacional. "
            "Evito sonar como un formulario y muestro genuino interés."
        )
    elif stage == "ask_last_hour":
        context += (
            "En esta etapa, pregunto al usuario qué hizo en la última hora. "
            "Soy específico sobre el rango de tiempo y muestro curiosidad genuina. "
            "Formulo la pregunta de manera conversacional."
        )
    elif stage == "clarifier_last_hour":
        context += (
            "En esta etapa, profundizo con preguntas de clarificación sobre actividades pasadas. "
            "Pregunto por detalles específicos como qué, cuándo, dónde, con quién, por qué. "
            "Las preguntas deben ser naturales y mostrar interés real."
        )
    elif stage == "ask_next_hour":
        context += (
            "En esta etapa, pregunto al usuario qué planea hacer en la próxima hora. "
            "Soy específico sobre el rango de tiempo y muestro curiosidad genuina. "
            "Formulo la pregunta de manera conversacional."
        )
    elif stage == "clarifier_next_hour":
        context += (
            "En esta etapa, profundizo con preguntas de clarificación sobre planes futuros. "
            "Pregunto por detalles específicos como qué, cuándo, dónde, con quién, por qué. "
            "Las preguntas deben ser naturales y mostrar interés real."
        )
    elif stage == "final":
        context += (
            "En esta etapa, cierro la conversación de forma amigable. "
            "Resumo lo que he aprendido, ofrezco algún insight valioso y "
            "preparo al usuario para la próxima interacción."
        )
    
    return context

def ask_gpt_in_context(db, user_id: str, user_prompt: str, stage: str) -> str:
    """Utiliza el modelo de lenguaje con contexto específico para cada etapa."""
    system_text = build_system_context(db, user_id, stage)
    
    # Obtener las últimas conversaciones para contexto
    logs = db.get_user_conversation(user_id, limit=8)
    
    # Construir el mensaje para el modelo
    chat = [{"role": "system", "content": system_text}]
    
    for msg in logs:
        role = "assistant" if msg["role"] == "assistant" else "user"
        chat.append({"role": role, "content": msg["content"]})
    
    # Añadir el prompt actual
    chat.append({"role": "user", "content": user_prompt})
    
    # Guardar el prompt en logs para depuración
    db.save_conversation_message(user_id, "system", f"GPT Prompt: {user_prompt}", {"step": stage})
    
    # Obtener respuesta del modelo
    response = ask_gpt_chat(chat, model="gpt-3.5-turbo", temperature=0.7)
    
    return response if response else "¿Podrías repetirme lo que necesitas?"

def generate_profile_request(db, user_id: str, missing_fields: list) -> str:
    """Genera una solicitud amigable para completar campos faltantes del perfil."""
    state = db.get_state(user_id)
    current_name = state.get("name", "")
    
    # Crear prompt personalizado según los campos faltantes
    if "nombre" in missing_fields:
        if not current_name:
            prompt = "Hola, soy Zendell, tu asistente personal. Me encantaría conocerte mejor. ¿Cómo te llamas?"
        else:
            needed = ", ".join([f for f in missing_fields if f != "nombre"])
            prompt = f"Hola {current_name}, me encantaría conocerte mejor. Necesito saber sobre tu {needed}."
    else:
        needed = ", ".join(missing_fields)
        prompt = f"Hola {current_name}, para conocerte mejor, me gustaría saber más sobre tu {needed}."
    
    return ask_gpt_in_context(db, user_id, prompt, "ask_profile")

def generate_last_hour_question(db, user_id: str, time_ranges: dict) -> str:
    """Genera una pregunta natural sobre lo que hizo el usuario en la última hora."""
    state = db.get_state(user_id)
    name = state.get("name", "")
    
    prompt = (
        f"¿Qué has estado haciendo entre las {time_ranges['last_hour']['start']} y las "
        f"{time_ranges['last_hour']['end']}, {name}? Me interesa saber cómo ha ido tu última hora."
    )
    
    return ask_gpt_in_context(db, user_id, prompt, "ask_last_hour")

def generate_next_hour_question(db, user_id: str, time_ranges: dict) -> str:
    """Genera una pregunta natural sobre lo que planea hacer el usuario en la próxima hora."""
    state = db.get_state(user_id)
    name = state.get("name", "")
    
    prompt = (
        f"¿Qué planes tienes para la próxima hora, de {time_ranges['next_hour']['start']} a "
        f"{time_ranges['next_hour']['end']}, {name}? Me interesa saber qué harás."
    )
    
    return ask_gpt_in_context(db, user_id, prompt, "ask_next_hour")

def generate_clarification_message(db, user_id: str, questions: list, stage: str) -> str:
    """Genera un mensaje con preguntas de clarificación de forma natural."""
    # Construir un prompt con las preguntas
    prompt = "Para entender mejor, me gustaría preguntarte: " + "; ".join(questions)
    
    return ask_gpt_in_context(db, user_id, prompt, stage)

def generate_final_message(db, user_id: str, global_state: dict) -> str:
    """Genera un mensaje final con insights y recomendaciones."""
    analysis = global_state.get("analysis", {}).get("summary", "")
    recommendations = global_state.get("recommendation", [])
    
    # Construir un prompt con el análisis y las recomendaciones
    prompt = (
        f"Basado en nuestra conversación, he observado que: {analysis} "
        f"Algunas sugerencias que podrían ayudarte: {'; '.join(recommendations)}. "
        f"¿Hay algo más en lo que pueda ayudarte antes de terminar esta interacción?"
    )
    
    return ask_gpt_in_context(db, user_id, prompt, "final")

def generate_closing_message(db, user_id: str) -> str:
    """Genera un mensaje de cierre para la conversación."""
    prompt = (
        "Gracias por conversar conmigo. He guardado la información que compartiste. "
        "Volveré a contactarte pronto para seguir aprendiendo sobre ti y ayudarte mejor. "
        "¡Hasta pronto!"
    )
    
    return ask_gpt_in_context(db, user_id, prompt, "final")

def update_long_term_memory(db, memory_manager, user_id: str) -> None:
    """Actualiza la memoria a largo plazo con la información recopilada."""
    # Generar insights sobre las actividades (1 de cada 5 veces)
    import random
    if random.random() < 0.2:  # 20% de probabilidad
        memory_manager.get_activity_insights(user_id)
    
    # Generar resumen de conversación (1 de cada 3 veces)
    if random.random() < 0.33:  # 33% de probabilidad
        memory_manager.summarize_conversation_history(user_id)
    
    # Actualizar perfil a largo plazo (1 de cada 10 veces)
    if random.random() < 0.1:  # 10% de probabilidad
        memory_manager.generate_long_term_reflection(user_id)