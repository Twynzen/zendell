# zendell/agents/analyzer.py

from typing import Dict, Any, List
from collections import Counter
from datetime import datetime
from zendell.services.llm_provider import ask_gpt

def analyzer_node(global_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analiza las actividades del usuario para generar insights valiosos.
    
    Este nodo:
    1. Examina las actividades recopiladas hasta el momento
    2. Identifica patrones, categorías predominantes y prioridades
    3. Genera un análisis profundo sobre el estado y comportamiento del usuario
    4. Almacena el análisis para uso posterior por otros agentes
    
    Args:
        global_state: Estado global que contiene las actividades y contexto
        
    Returns:
        Dict[str, Any]: Estado global actualizado con el análisis
    """
    db = global_state["db"]
    user_id = global_state.get("user_id", "unknown_user")
    activities = global_state.get("activities", [])
    
    # Si no hay actividades, no podemos realizar un análisis
    if not activities:
        global_state["analysis"] = {
            "summary": "No hay actividades registradas para analizar.",
            "patterns": [],
            "tone": "neutral",
            "insights": []
        }
        return global_state
    
    # Separar actividades por contexto temporal (pasado/futuro)
    past_activities = [act for act in activities if act.get("time_context") == "past"]
    future_activities = [act for act in activities if act.get("time_context") == "future"]
    
    # Analizar categorías de actividades
    all_categories = [act.get("category", "") for act in activities]
    category_counts = Counter(all_categories)
    
    # Registrar timestamp del análisis
    timestamp = datetime.utcnow().isoformat()
    
    # Si tenemos actividades pasadas, analizarlas
    past_analysis = analyze_past_activities(past_activities) if past_activities else ""
    
    # Si tenemos actividades futuras, analizarlas
    future_analysis = analyze_future_activities(future_activities) if future_activities else ""
    
    # Analizar la relación entre pasado y futuro
    relationship_analysis = ""
    if past_activities and future_activities:
        relationship_analysis = analyze_relationship(past_activities, future_activities)
    
    # Consolidar el análisis completo
    complete_analysis = generate_complete_analysis(
        past_analysis, 
        future_analysis, 
        relationship_analysis, 
        dict(category_counts)
    )
    
    # Extraer insights específicos
    insights = extract_insights(activities, complete_analysis)
    
    # Analizar el tono general
    tone = analyze_tone(activities, complete_analysis)
    
    # Crear objeto de análisis completo
    analysis_object = {
        "summary": complete_analysis,
        "past_analysis": past_analysis,
        "future_analysis": future_analysis,
        "relationship": relationship_analysis,
        "categories": dict(category_counts),
        "tone": tone,
        "insights": insights,
        "timestamp": timestamp
    }
    
    # Actualizar global_state con el análisis
    global_state["analysis"] = analysis_object
    
    # Guardar en la base de datos
    db.save_conversation_message(
        user_id, 
        "system", 
        f"Análisis: {complete_analysis}", 
        {"step": "analyzer_node"}
    )
    
    # Actualizar el estado del usuario con un resumen del análisis
    current_state = db.get_state(user_id)
    
    # Añadir a short_term_info un resumen breve
    shortened_analysis = complete_analysis[:100] + "..." if len(complete_analysis) > 100 else complete_analysis
    db.add_to_short_term_info(user_id, f"Analysis: {shortened_analysis}")
    
    # Generar una memoria del sistema con este análisis
    memory_data = {
        "content": complete_analysis,
        "type": "activity_analysis",
        "relevance": 8,
        "created_at": timestamp
    }
    db.add_system_memory(memory_data)
    
    return global_state

def analyze_past_activities(activities: List[Dict[str, Any]]) -> str:
    """
    Analiza las actividades pasadas para identificar patrones y estado.
    
    Args:
        activities: Lista de actividades pasadas
        
    Returns:
        str: Análisis de las actividades pasadas
    """
    if not activities:
        return ""
    
    # Extraer información relevante para el análisis
    titles = [act.get("title", "") for act in activities]
    categories = [act.get("category", "") for act in activities]
    
    # Buscar clarificaciones para información adicional
    clarifications = []
    for act in activities:
        clarifier_responses = act.get("clarifier_responses", [])
        for resp in clarifier_responses:
            if isinstance(resp, dict) and "question" in resp and "answer" in resp:
                clarifications.append(f"Q: {resp['question']} - A: {resp['answer']}")
    
    # Crear prompt para el análisis
    prompt = (
        f"Analiza las siguientes actividades PASADAS del usuario:\n"
        f"Títulos: {titles}\n"
        f"Categorías: {categories}\n"
        f"Clarificaciones: {clarifications}\n\n"
        f"Proporciona un análisis conciso (4-5 frases) de estas actividades pasadas que incluya:\n"
        f"1. Qué sugieren sobre el estado actual del usuario (ocupado, relajado, productivo, etc.)\n"
        f"2. Posibles prioridades o focos de atención\n"
        f"3. Cualquier patrón o comportamiento notable\n"
        f"Mantén el análisis objetivo y basado estrictamente en los datos proporcionados."
    )
    
    analysis = ask_gpt(prompt)
    return analysis

def analyze_future_activities(activities: List[Dict[str, Any]]) -> str:
    """
    Analiza las actividades futuras para identificar intenciones y planes.
    
    Args:
        activities: Lista de actividades futuras
        
    Returns:
        str: Análisis de las actividades futuras
    """
    if not activities:
        return ""
    
    # Extraer información relevante para el análisis
    titles = [act.get("title", "") for act in activities]
    categories = [act.get("category", "") for act in activities]
    
    # Buscar clarificaciones para información adicional
    clarifications = []
    for act in activities:
        clarifier_responses = act.get("clarifier_responses", [])
        for resp in clarifier_responses:
            if isinstance(resp, dict) and "question" in resp and "answer" in resp:
                clarifications.append(f"Q: {resp['question']} - A: {resp['answer']}")
    
    # Crear prompt para el análisis
    prompt = (
        f"Analiza las siguientes actividades FUTURAS (planeadas) del usuario:\n"
        f"Títulos: {titles}\n"
        f"Categorías: {categories}\n"
        f"Clarificaciones: {clarifications}\n\n"
        f"Proporciona un análisis conciso (4-5 frases) de estos planes que incluya:\n"
        f"1. Qué sugieren sobre las intenciones o prioridades inmediatas\n"
        f"2. Posible estado emocional o mental basado en lo planeado\n"
        f"3. Cualquier objetivo o meta implícita\n"
        f"Mantén el análisis objetivo y basado estrictamente en los datos proporcionados."
    )
    
    analysis = ask_gpt(prompt)
    return analysis

def analyze_relationship(past_activities: List[Dict[str, Any]], future_activities: List[Dict[str, Any]]) -> str:
    """
    Analiza la relación entre actividades pasadas y futuras.
    
    Args:
        past_activities: Lista de actividades pasadas
        future_activities: Lista de actividades futuras
        
    Returns:
        str: Análisis de la relación entre pasado y futuro
    """
    # Extraer títulos para comparación
    past_titles = [act.get("title", "") for act in past_activities]
    future_titles = [act.get("title", "") for act in future_activities]
    
    # Extraer categorías para comparación
    past_categories = [act.get("category", "") for act in past_activities]
    future_categories = [act.get("category", "") for act in future_activities]
    
    # Crear prompt para el análisis
    prompt = (
        f"Compara estas actividades PASADAS: {past_titles} ({past_categories}) "
        f"con estas actividades FUTURAS: {future_titles} ({future_categories}).\n\n"
        f"Proporciona un análisis conciso (3-4 frases) que examine:\n"
        f"1. Continuidad o cambio entre lo que ha hecho y lo que planea hacer\n"
        f"2. Posible evolución de prioridades o estado emocional\n"
        f"3. Cualquier insight sobre cómo su pasado inmediato podría influir en sus planes\n"
        f"Mantén el análisis objetivo y basado estrictamente en los datos proporcionados."
    )
    
    analysis = ask_gpt(prompt)
    return analysis

def generate_complete_analysis(past_analysis: str, future_analysis: str, relationship_analysis: str, categories: Dict[str, int]) -> str:
    """
    Genera un análisis completo consolidando todos los análisis parciales.
    
    Args:
        past_analysis: Análisis de actividades pasadas
        future_analysis: Análisis de actividades futuras
        relationship_analysis: Análisis de la relación entre pasado y futuro
        categories: Conteo de categorías de actividades
        
    Returns:
        str: Análisis completo consolidado
    """
    # Si no hay ningún análisis, devolver mensaje por defecto
    if not past_analysis and not future_analysis:
        return "No hay suficientes actividades para realizar un análisis completo."
    
    # Preparar componentes para el análisis
    components = []
    
    if past_analysis:
        components.append(f"Análisis de actividades pasadas: {past_analysis}")
    
    if future_analysis:
        components.append(f"Análisis de planes futuros: {future_analysis}")
    
    if relationship_analysis:
        components.append(f"Relación entre pasado y futuro: {relationship_analysis}")
    
    if categories:
        top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]
        top_cats_str = ", ".join([f"{cat} ({count})" for cat, count in top_categories])
        components.append(f"Categorías principales: {top_cats_str}")
    
    # Crear prompt para el análisis completo
    prompt = (
        f"Con base en estos análisis parciales:\n\n"
        f"{' '.join(components)}\n\n"
        f"Genera un análisis integral y cohesivo (6-8 frases) que sintetice todos estos elementos "
        f"en una evaluación clara y perspicaz del estado actual del usuario, sus prioridades "
        f"y posibles necesidades o áreas de atención. Evita repetir información y céntrate "
        f"en ofrecer una visión holística y valiosa."
    )
    
    complete_analysis = ask_gpt(prompt)
    return complete_analysis

def extract_insights(activities: List[Dict[str, Any]], complete_analysis: str) -> List[str]:
    """
    Extrae insights específicos y accionables del análisis completo.
    
    Args:
        activities: Lista de todas las actividades
        complete_analysis: Análisis completo generado
        
    Returns:
        List[str]: Lista de insights específicos
    """
    prompt = (
        f"Basado en estas actividades: {[a.get('title', '') for a in activities]}\n"
        f"Y este análisis: {complete_analysis}\n\n"
        f"Extrae 3-5 insights específicos y valiosos sobre el usuario. "
        f"Cada insight debe ser una observación concreta, no obvia, que revele algo "
        f"importante sobre sus patrones, necesidades, estado o prioridades. "
        f"Formato: Lista de frases cortas y directas."
    )
    
    insights_text = ask_gpt(prompt)
    
    # Procesar el texto para obtener una lista
    insights = [insight.strip() for insight in insights_text.split("\n") if insight.strip()]
    
    # Si no se pudieron extraer insights o el formato no es el esperado
    if not insights:
        # Crear algunos insights genéricos basados en las categorías
        categories = [act.get("category", "") for act in activities]
        category_counts = Counter(categories)
        
        top_category = category_counts.most_common(1)[0][0] if category_counts else "Desconocida"
        
        insights = [
            f"La categoría predominante es {top_category}, lo que sugiere un enfoque en esta área.",
            "El usuario muestra un patrón de actividad que refleja sus prioridades actuales.",
            "Las actividades reflejan un equilibrio entre diferentes áreas de su vida."
        ]
    
    return insights[:5]  # Limitar a 5 insights máximo

def analyze_tone(activities: List[Dict[str, Any]], analysis: str) -> str:
    """
    Analiza el tono general del usuario basado en sus actividades.
    
    Args:
        activities: Lista de todas las actividades
        analysis: Análisis completo generado
        
    Returns:
        str: Descripción del tono detectado
    """
    # Extraer textos relevantes para analizar el tono
    texts = []
    
    # Añadir títulos de actividades
    texts.extend([act.get("title", "") for act in activities])
    
    # Añadir respuestas de clarificación
    for act in activities:
        clarifier_responses = act.get("clarifier_responses", [])
        for resp in clarifier_responses:
            if isinstance(resp, dict) and "answer" in resp:
                texts.append(resp["answer"])
    
    # Si no hay suficiente texto, usar un tono neutral
    if not texts:
        return "neutral"
    
    # Combinar todos los textos
    combined_text = " ".join(texts)
    
    # Crear prompt para analizar el tono
    prompt = (
        f"Analiza el tono emocional en este texto: '{combined_text}'\n"
        f"Determina el tono predominante (ej: entusiasta, neutral, preocupado, optimista, etc.) "
        f"basándote en las palabras, frases y contexto. Responde con una sola palabra o frase corta."
    )
    
    tone = ask_gpt(prompt).strip().lower()
    
    # Si la respuesta es muy larga, simplificarla
    if len(tone) > 20:
        default_tones = ["neutral", "positivo", "negativo", "entusiasta", "preocupado"]
        for default_tone in default_tones:
            if default_tone in tone:
                return default_tone
        return "neutral"
    
    return tone