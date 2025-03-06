# zendell/agents/recommender.py

from typing import Dict, Any, List
from datetime import datetime
from zendell.services.llm_provider import ask_gpt

def recommender_node(global_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Genera recomendaciones personalizadas basadas en el análisis de actividades.
    
    Este nodo:
    1. Utiliza el análisis del analyzer_node para entender el contexto
    2. Genera recomendaciones prácticas y personalizadas
    3. Prioriza las recomendaciones según relevancia y valor para el usuario
    4. Almacena las recomendaciones para uso futuro
    
    Args:
        global_state: Estado global que contiene el análisis y contexto
        
    Returns:
        Dict[str, Any]: Estado global actualizado con recomendaciones
    """
    user_id = global_state.get("user_id", "unknown_user")
    analysis_info = global_state.get("analysis", {})
    db = global_state.get("db")
    
    # Si no hay análisis disponible, no podemos generar recomendaciones
    if not analysis_info:
        global_state["recommendation"] = ["No hay suficiente información para generar recomendaciones."]
        return global_state
    
    # Obtener información relevante para las recomendaciones
    summary_text = analysis_info.get("summary", "")
    insights = analysis_info.get("insights", [])
    tone = analysis_info.get("tone", "neutral")
    
    # Obtener información adicional del perfil del usuario
    user_profile = db.get_user_profile(user_id)
    general_info = user_profile.general_info
    
    # Preparar contexto para las recomendaciones
    context = {
        "summary": summary_text,
        "insights": insights,
        "tone": tone,
        "name": general_info.name or "Usuario",
        "gustos": general_info.gustos,
        "metas": general_info.metas
    }
    
    # Generar recomendaciones basadas en el análisis y contexto
    recommendations = generate_recommendations(context)
    
    # Organizar las recomendaciones por prioridad
    prioritized_recommendations = prioritize_recommendations(recommendations, context)
    
    # Actualizar global_state con las recomendaciones
    global_state["recommendation"] = prioritized_recommendations
    
    # Guardar recomendaciones en la base de datos
    save_recommendations(db, user_id, prioritized_recommendations, summary_text)
    
    return global_state

def generate_recommendations(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Genera recomendaciones basadas en el contexto proporcionado.
    
    Args:
        context: Información contextual para generar recomendaciones
        
    Returns:
        List[Dict[str, Any]]: Lista de recomendaciones con metadatos
    """
    # Extraer información relevante del contexto
    summary = context.get("summary", "")
    insights = context.get("insights", [])
    user_name = context.get("name", "Usuario")
    gustos = context.get("gustos", "")
    metas = context.get("metas", "")
    
    # Construir prompt para generar recomendaciones
    insights_text = "\n".join([f"- {insight}" for insight in insights])
    
    prompt = (
        f"Basado en este análisis de las actividades de {user_name}:\n"
        f"{summary}\n\n"
        f"Y estos insights:\n{insights_text}\n\n"
        f"Considerando sus gustos ({gustos}) y metas ({metas}), "
        f"genera 3-5 recomendaciones prácticas, específicas y personalizadas que puedan "
        f"ayudarle a mejorar su bienestar, productividad o satisfacción personal. "
        f"Cada recomendación debe incluir:\n"
        f"1. Una acción concreta y realizable\n"
        f"2. Una breve justificación basada en el análisis\n"
        f"3. Un beneficio esperado\n\n"
        f"Formato: Lista numerada donde cada recomendación tenga título y descripción breve."
    )
    
    recommendations_text = ask_gpt(prompt)
    
    # Procesar el texto para convertirlo en una estructura de datos
    raw_recommendations = parse_recommendations(recommendations_text)
    
    # Añadir metadatos a cada recomendación
    recommendations = []
    for i, rec in enumerate(raw_recommendations):
        rec_object = {
            "id": f"rec_{datetime.utcnow().strftime('%Y%m%d')}_{i+1}",
            "text": rec,
            "category": classify_recommendation(rec),
            "priority": i + 1,  # Prioridad inicial basada en el orden
            "created_at": datetime.utcnow().isoformat(),
            "context": {
                "based_on_summary": summary[:100] + "..." if len(summary) > 100 else summary,
                "based_on_insights": insights[:2] if insights else []
            }
        }
        recommendations.append(rec_object)
    
    return recommendations

def parse_recommendations(text: str) -> List[str]:
    """
    Parsea el texto de recomendaciones para convertirlo en lista.
    
    Args:
        text: Texto de recomendaciones generado por el LLM
        
    Returns:
        List[str]: Lista de recomendaciones limpias
    """
    # Dividir por líneas y limpiar
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    # Preparar para procesar las recomendaciones
    recommendations = []
    current_rec = ""
    
    for line in lines:
        # Detectar si es una nueva recomendación (empieza con número o tiene "Recomendación")
        if (line[0].isdigit() and line[1] in [".", ")", ":"]) or "Recomendación" in line:
            # Si ya teníamos una recomendación acumulada, guardarla
            if current_rec:
                recommendations.append(current_rec)
            # Iniciar nueva recomendación
            current_rec = line
        else:
            # Continuar con la recomendación actual
            current_rec += " " + line
    
    # No olvidar la última recomendación
    if current_rec:
        recommendations.append(current_rec)
    
    # Si no se pudieron extraer recomendaciones correctamente
    if not recommendations:
        # Intentar dividir por doble salto de línea
        recommendations = [rec.strip() for rec in text.split("\n\n") if rec.strip()]
    
    # Si aún no hay recomendaciones, usar el texto completo
    if not recommendations:
        recommendations = [text]
    
    return recommendations

def classify_recommendation(recommendation: str) -> str:
    """
    Clasifica una recomendación en una categoría.
    
    Args:
        recommendation: Texto de la recomendación
        
    Returns:
        str: Categoría asignada
    """
    prompt = (
        f"Clasifica esta recomendación en UNA de las siguientes categorías:\n"
        f"- Productividad\n"
        f"- Bienestar\n"
        f"- Relaciones\n"
        f"- Desarrollo Personal\n"
        f"- Salud Física\n"
        f"- Salud Mental\n"
        f"- Equilibrio\n\n"
        f"Recomendación: '{recommendation}'\n\n"
        f"Responde SOLO con el nombre de la categoría, sin explicación."
    )
    
    category = ask_gpt(prompt).strip()
    
    # Verificar que la categoría es válida
    valid_categories = [
        "Productividad", "Bienestar", "Relaciones", "Desarrollo Personal",
        "Salud Física", "Salud Mental", "Equilibrio"
    ]
    
    if category not in valid_categories:
        # Buscar la categoría más similar
        for valid_cat in valid_categories:
            if valid_cat.lower() in category.lower():
                return valid_cat
        # Si no hay coincidencia, usar una categoría por defecto
        return "Bienestar"
    
    return category

def prioritize_recommendations(recommendations: List[Dict[str, Any]], context: Dict[str, Any]) -> List[str]:
    """
    Prioriza las recomendaciones según relevancia y valor para el usuario.
    
    Args:
        recommendations: Lista de recomendaciones con metadatos
        context: Información contextual del usuario
        
    Returns:
        List[str]: Lista de recomendaciones ordenadas por prioridad
    """
    # Si hay pocas recomendaciones, no es necesario priorizar
    if len(recommendations) <= 3:
        return [rec["text"] for rec in recommendations]
    
    # Extraer contexto relevante
    tone = context.get("tone", "neutral")
    metas = context.get("metas", "")
    
    # Ajustar prioridad según categoría y tono
    for rec in recommendations:
        category = rec["category"]
        priority = rec["priority"]
        
        # Ajustar según el tono detectado
        if tone in ["preocupado", "estresado", "ansioso", "negativo"]:
            if category in ["Bienestar", "Salud Mental", "Equilibrio"]:
                priority -= 1  # Aumentar prioridad (menor número = mayor prioridad)
        elif tone in ["entusiasta", "positivo", "motivado"]:
            if category in ["Productividad", "Desarrollo Personal"]:
                priority -= 1
        
        # Ajustar según metas del usuario
        if metas:
            if category.lower() in metas.lower():
                priority -= 1
        
        # Actualizar prioridad
        rec["priority"] = max(1, priority)  # Mínimo 1
    
    # Ordenar por prioridad
    sorted_recommendations = sorted(recommendations, key=lambda x: x["priority"])
    
    # Limitar a 5 recomendaciones máximo
    top_recommendations = sorted_recommendations[:5]
    
    # Extraer solo el texto
    return [rec["text"] for rec in top_recommendations]

def save_recommendations(db, user_id: str, recommendations: List[str], analysis_summary: str) -> None:
    """
    Guarda las recomendaciones en la base de datos.
    
    Args:
        db: Gestor de base de datos
        user_id: ID del usuario
        recommendations: Lista de recomendaciones
        analysis_summary: Resumen del análisis que generó las recomendaciones
    """
    # Guardar en los logs de conversación
    recommendations_text = "\n".join([f"- {rec}" for rec in recommendations])
    db.save_conversation_message(
        user_id=user_id,
        role="assistant",
        content=recommendations_text,
        extra_data={"step": "recommender_node"}
    )
    
    # Actualizar el estado del usuario con un resumen
    rec_summary = recommendations[0] if recommendations else "No se generaron recomendaciones."
    db.add_to_short_term_info(user_id, f"Recommender => {rec_summary}")
    
    # Guardar como memoria del sistema
    timestamp = datetime.utcnow().isoformat()
    memory_data = {
        "content": f"Recomendaciones basadas en: {analysis_summary}\n\n{recommendations_text}",
        "type": "recommendation",
        "relevance": 7,
        "created_at": timestamp
    }
    db.add_system_memory(memory_data)