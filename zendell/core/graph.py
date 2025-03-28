# zendell/core/graph.py
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List, Dict, Any, Literal, Union, Optional, Annotated
from datetime import datetime
from zendell.agents.activity_collector import activity_collector_node
from zendell.agents.clarifier import clarifier_node, process_clarifier_response
from zendell.agents.analyzer import analyzer_node
from zendell.agents.recommender import recommender_node
from core.utils import get_timestamp

# Definición completa del estado para LangGraph
class GlobalState(TypedDict):
    # Información del usuario
    user_id: str
    customer_name: str
    
    # Datos de la conversación actual
    last_message: str
    current_stage: str
    conversation_context: List[Dict[str, Any]]
    
    # Actividades y análisis
    activities: List[Dict[str, Any]]
    clarification_questions: List[str]
    clarifier_responses: List[str]
    analysis: Dict[str, Any]
    recommendation: List[str]
    
    # Estado de memoria
    short_term_info: List[str]
    memory_data: Dict[str, Any]
    
    # Salida final
    final_text: Optional[str]
    
    # Referencias a servicios
    db: Any
    memory_manager: Any

# Función para imprimir seguimiento del grafo
def trace_step(name: str, state: GlobalState) -> GlobalState:
    """Registra la ejecución de cada nodo para seguimiento."""
    print(f"{get_timestamp()}", f"[LANGGRAPH] Ejecutando nodo: {name}")
    return state

# Nodo para comprender el perfil del usuario
def profile_manager_node(state: GlobalState) -> GlobalState:
    """Gestiona la información del perfil del usuario."""
    user_id = state["user_id"]
    db = state["db"]
    last_message = state["last_message"]
    
    # Extraer información del perfil del mensaje
    try:
        extracted_info = db.extract_and_update_user_info(user_id, last_message)
        
        # Actualizar el nombre en el estado global
        if "name" in extracted_info and extracted_info["name"]:
            state["customer_name"] = extracted_info["name"]
            
        # Registrar en la memoria a corto plazo
        db.add_to_short_term_info(user_id, f"[Profile] Información extraída: {extracted_info}")
        
    except Exception as e:
        print(f"{get_timestamp()}", f"[LANGGRAPH] Error en profile_manager_node: {e}")
    
    return state

# Nodo para generar respuestas finales
def response_generator_node(state: GlobalState) -> GlobalState:
    """Genera la respuesta final para el usuario."""
    user_id = state["user_id"]
    db = state["db"]
    current_stage = state.get("current_stage", "initial")
    
    # Seleccionar la plantilla de respuesta según la etapa
    if current_stage == "initial" or current_stage == "ask_profile":
        prompt = "Por favor, generar un mensaje amistoso pidiendo información básica al usuario (nombre, ocupación, gustos)."
    elif current_stage == "ask_last_hour":
        prompt = "Generar una pregunta sobre qué ha estado haciendo el usuario en la última hora."
    elif current_stage == "clarifier_last_hour":
        if state.get("clarification_questions"):
            questions = ", ".join(state.get("clarification_questions", []))
            prompt = f"Formular de manera conversacional estas preguntas: {questions}"
        else:
            prompt = "Preguntar detalles adicionales sobre lo que ha estado haciendo."
    elif current_stage == "ask_next_hour":
        prompt = "Preguntar qué planea hacer en la próxima hora."
    elif current_stage == "clarifier_next_hour":
        if state.get("clarification_questions"):
            questions = ", ".join(state.get("clarification_questions", []))
            prompt = f"Formular de manera conversacional estas preguntas: {questions}"
        else:
            prompt = "Preguntar detalles adicionales sobre sus planes."
    elif current_stage == "final":
        # Si hay recomendaciones, incluirlas
        recommendations = state.get("recommendation", [])
        analysis = state.get("analysis", {}).get("summary", "")
        
        prompt = f"Generar un mensaje de cierre que resuma lo aprendido: {analysis}. "
        if recommendations:
            prompt += f"Incluir estas recomendaciones: {', '.join(recommendations)}."
        else:
            prompt += "Ofrecer un cierre amistoso sin recomendaciones específicas."
    else:
        prompt = "Generar una respuesta natural y amistosa al mensaje del usuario."
    
    try:
        from zendell.services.llm_provider import ask_gpt
        response = ask_gpt(prompt)
        
        if not response:
            response = "Gracias por compartir esa información. ¿Hay algo más en que pueda ayudarte?"
            
        # Almacenar la respuesta en el estado
        state["final_text"] = response
        
        # Guardar en la base de datos
        db.save_conversation_message(user_id, "assistant", response, {"step": current_stage})
        
    except Exception as e:
        print(f"{get_timestamp()}", f"[LANGGRAPH] Error en response_generator_node: {e}")
        state["final_text"] = "Gracias por tu mensaje. ¿Hay algo más en que pueda ayudarte?"
    
    return state

# Nodo para actualizar la memoria
def memory_update_node(state: GlobalState) -> GlobalState:
    """Actualiza la memoria del sistema con la información nueva."""
    user_id = state["user_id"]
    memory_manager = state.get("memory_manager")
    
    if not memory_manager:
        return state
    
    try:
        # Actualizar memoria a corto plazo
        memory_manager.add_observation(
            user_id, 
            f"Mensaje recibido: {state['last_message']}", 
            "user_message"
        )
        
        # Si hay análisis, actualizar memoria
        if state.get("analysis") and state["analysis"].get("summary"):
            memory_manager.add_observation(
                user_id,
                f"Análisis: {state['analysis']['summary']}",
                "analysis"
            )
            
        # Ocasionalmente generar reflexiones a largo plazo
        import random
        if random.random() < 0.1:  # 10% de probabilidad
            memory_manager.generate_long_term_reflection(user_id)
    
    except Exception as e:
        print(f"{get_timestamp()}", f"[LANGGRAPH] Error en memory_update_node: {e}")
    
    return state

# Funciones para determinar la transición entre estados
def determine_next_stage(state: GlobalState) -> Literal["ask_profile", "ask_last_hour", "clarifier_last_hour", "ask_next_hour", "clarifier_next_hour", "final"]:
    """Determina la siguiente etapa de la conversación."""
    current_stage = state.get("current_stage", "initial")
    user_id = state["user_id"]
    db = state["db"]
    
    # Verificar si faltan campos en el perfil
    st = db.get_state(user_id)
    missing_fields = []
    
    # Comprobar campos del perfil
    if not st.get("name") or st.get("name") == "Desconocido":
        missing_fields.append("nombre")
    
    general_info = st.get("general_info", {})
    if not general_info.get("ocupacion"):
        missing_fields.append("ocupacion")
    if not general_info.get("gustos"):
        missing_fields.append("gustos")
    if not general_info.get("metas"):
        missing_fields.append("metas")
    
    # Lógica de transición según la etapa actual
    if current_stage == "initial":
        if missing_fields:
            return "ask_profile"
        else:
            return "ask_last_hour"
    
    elif current_stage == "ask_profile":
        if missing_fields:
            return "ask_profile"  # Seguir pidiendo información
        else:
            return "ask_last_hour"
    
    elif current_stage == "ask_last_hour":
        # Verificar si hay preguntas de clarificación
        clarification_questions = state.get("clarification_questions", [])
        if clarification_questions:
            return "clarifier_last_hour"
        else:
            return "ask_next_hour"
    
    elif current_stage == "clarifier_last_hour":
        return "ask_next_hour"
    
    elif current_stage == "ask_next_hour":
        # Verificar si hay preguntas de clarificación
        clarification_questions = state.get("clarification_questions", [])
        if clarification_questions:
            return "clarifier_next_hour"
        else:
            return "final"
    
    elif current_stage == "clarifier_next_hour":
        return "final"
    
    else:
        # Si estamos en una etapa desconocida, ir a ask_last_hour
        return "ask_last_hour"

# Construcción del grafo
def build_conversation_graph():
    """Construye el grafo de conversación completo."""
    # Inicializar el grafo
    builder = StateGraph(GlobalState)
    
    # Añadir nodos con trazas para depuración
    builder.add_node("profile_manager", lambda s: profile_manager_node(trace_step("profile_manager", s)))
    builder.add_node("activity_collector", lambda s: activity_collector_node(trace_step("activity_collector", s)))
    builder.add_node("clarifier", lambda s: clarifier_node(trace_step("clarifier", s)))
    builder.add_node("process_clarifier", lambda s: process_clarifier_response(trace_step("process_clarifier", s)))
    builder.add_node("analyzer", lambda s: analyzer_node(trace_step("analyzer", s)))
    builder.add_node("recommender", lambda s: recommender_node(trace_step("recommender", s)))
    builder.add_node("memory_update", lambda s: memory_update_node(trace_step("memory_update", s)))
    builder.add_node("response_generator", lambda s: response_generator_node(trace_step("response_generator", s)))
    
    # Definir el flujo principal
    builder.add_edge(START, "profile_manager")
    builder.add_edge("profile_manager", "activity_collector")
    
    # Añadir transiciones condicionales basadas en la etapa actual
    builder.add_conditional_edges(
        "activity_collector",
        determine_next_stage,
        {
            "ask_profile": "response_generator",
            "ask_last_hour": "clarifier",
            "clarifier_last_hour": "clarifier",
            "ask_next_hour": "clarifier",
            "clarifier_next_hour": "clarifier",
            "final": "analyzer"
        }
    )
    
    # Completar el resto del flujo
    builder.add_edge("clarifier", "process_clarifier")
    builder.add_edge("process_clarifier", "response_generator")
    builder.add_edge("analyzer", "recommender")
    builder.add_edge("recommender", "memory_update")
    builder.add_edge("memory_update", "response_generator")
    builder.add_edge("response_generator", END)
    
    # Compilar el grafo
    return builder.compile()

# Crear el grafo
conversation_graph = build_conversation_graph()

# Exportar el grafo para visualización (opcional)
try:
    from langgraph.graph import save
    save(conversation_graph, "zendell_conversation_graph.json")
    print(f"{get_timestamp()}", "[LANGGRAPH] Grafo guardado para visualización")
except Exception as e:
    print(f"{get_timestamp()}", f"[LANGGRAPH] Error al guardar el grafo: {e}")