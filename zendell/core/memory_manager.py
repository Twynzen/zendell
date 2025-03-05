# zendell/core/memory_manager.py

from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from zendell.services.llm_provider import ask_gpt, ask_gpt_chat

class MemoryManager:
    """
    Gestor centralizado de memoria para el sistema multiagente.
    
    Esta clase se encarga de:
    1. Gestionar diferentes niveles de memoria (corto, medio y largo plazo)
    2. Generar resúmenes y reflexiones sobre la información acumulada
    3. Recuperar información relevante para el contexto actual
    4. Integrar conocimiento de diferentes fuentes
    """
    
    def __init__(self, db_manager):
        """Inicializa el gestor de memoria con un gestor de base de datos."""
        self.db = db_manager
    
    # ======== MÉTODOS DE MEMORIA A CORTO PLAZO ========
    
    def get_recent_context(self, user_id: str, limit: int = 8) -> List[Dict[str, Any]]:
        """Obtiene el contexto reciente de la conversación."""
        return self.db.get_user_conversation(user_id, limit)
    
    def get_current_state_summary(self, user_id: str) -> str:
        """Genera un resumen del estado actual del usuario."""
        state = self.db.get_state(user_id)
        
        # Obtener la etapa actual
        current_stage = state.get("conversation_stage", "unknown")
        
        # Obtener las notas a corto plazo más recientes
        short_term_notes = state.get("short_term_info", [])[-5:]
        
        # Obtener el estado de ánimo inferido
        mood = state.get("mood", "neutral")
        
        # Construir un resumen conciso
        summary = (
            f"Estado actual: {current_stage}. "
            f"Último contexto: {'; '.join(short_term_notes)}. "
            f"Estado de ánimo inferido: {mood}."
        )
        
        return summary
    
    def add_observation(self, user_id: str, observation: str, source: str) -> None:
        """Añade una observación a la memoria a corto plazo."""
        importance = self._evaluate_importance(observation)
        
        # Añadir a short_term_info en el estado del usuario
        self.db.add_to_short_term_info(user_id, f"[{source.upper()}] {observation}")
        
        # Si es importante, guardarla también como memoria del sistema
        if importance >= 6:
            memory_data = {
                "memory_id": str(ObjectId()),
                "content": observation,
                "type": "observation",
                "relevance": importance,
                "created_at": datetime.utcnow().isoformat(),
                "source": source
            }
            
            self.db.add_system_memory(memory_data)
    
    def _evaluate_importance(self, text: str) -> int:
        """Evalúa la importancia de un texto (1-10)."""
        # Un algoritmo simple: la longitud y la presencia de palabras clave
        importance_words = [
            "importante", "crucial", "vital", "esencial", "necesario",
            "significativo", "fundamental", "clave", "crítico", "urgente"
        ]
        
        base_importance = 5
        
        # Ajustar por longitud
        if len(text) > 200:
            base_importance += 1
            
        # Ajustar por palabras de importancia
        for word in importance_words:
            if word.lower() in text.lower():
                base_importance += 1
                break
        
        # Limitar al rango 1-10
        return max(1, min(10, base_importance))
    
    # ======== MÉTODOS DE MEMORIA A MEDIO PLAZO ========
    
    def get_activity_insights(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Obtiene insights sobre las actividades recientes del usuario."""
        # Calcular fecha límite
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        # Obtener actividades desde esa fecha
        pipeline = [
            {"$match": {
                "user_id": user_id,
                "timestamp": {"$gte": cutoff_date}
            }},
            {"$sort": {"timestamp": -1}}
        ]
        
        activities = list(self.db.activities_coll.aggregate(pipeline))
        
        if not activities:
            return {
                "patterns": "No hay suficientes actividades para identificar patrones.",
                "common_categories": {},
                "most_important": "",
                "insights": []
            }
        
        # Analizar categorías comunes
        categories = {}
        for activity in activities:
            category = activity.get("category", "Otra")
            if category in categories:
                categories[category] += 1
            else:
                categories[category] = 1
        
        # Ordenar por frecuencia
        sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        
        # Identificar actividad más importante
        most_important = max(activities, key=lambda x: x.get("importance", 0))
        
        # Generar insights con LLM
        prompt = (
            f"Analiza estas actividades recientes del usuario:\n\n{activities[:10]}\n\n"
            "Identifica 3-5 patrones o insights significativos sobre los hábitos, "
            "prioridades o comportamiento del usuario. Sé específico y basado en datos."
        )
        
        insights_text = ask_gpt(prompt)
        insights = [insight.strip() for insight in insights_text.split("\n") if insight.strip()]
        
        # Generar un resumen de patrones
        summary_prompt = (
            f"Basado en estas actividades: {activities[:10]}, "
            "resume en un párrafo conciso los patrones de comportamiento y prioridades del usuario."
        )
        
        patterns_summary = ask_gpt(summary_prompt)
        
        return {
            "patterns": patterns_summary,
            "common_categories": dict(sorted_categories[:5]),
            "most_important": most_important.get("title", ""),
            "insights": insights
        }
    
    def summarize_conversation_history(self, user_id: str, days: int = 3) -> str:
        """Genera un resumen de las conversaciones recientes."""
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        pipeline = [
            {"$match": {
                "user_id": user_id,
                "timestamp": {"$gte": cutoff_date}
            }},
            {"$sort": {"timestamp": 1}}
        ]
        
        messages = list(self.db.conversations_coll.aggregate(pipeline))
        
        if not messages:
            return "No hay conversaciones recientes para resumir."
        
        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content'][:100]}..."
            for msg in messages[:20]  # Limitar a 20 mensajes para evitar tokens excesivos
        ])
        
        prompt = (
            f"Resume esta conversación de forma concisa, capturando los temas principales, "
            f"el tono general y cualquier conclusión importante:\n\n{conversation_text}"
        )
        
        summary = ask_gpt(prompt)
        return summary
    
    # ======== MÉTODOS DE MEMORIA A LARGO PLAZO ========
    
    def get_user_profile_context(self, user_id: str) -> Dict[str, Any]:
        """Obtiene el contexto de perfil del usuario para razonamiento."""
        profile = self.db.get_user_profile(user_id)
        
        # Construir un diccionario con la información más relevante
        context = {
            "name": profile.general_info.name or "Desconocido",
            "occupation": profile.general_info.ocupacion,
            "interests": profile.general_info.gustos,
            "goals": profile.general_info.metas,
            "long_term_summary": profile.long_term_summary,
            "personality_traits": profile.personality_traits
        }
        
        return context
    
    def get_knowledge_context(self, user_id: str, query: str = "") -> str:
        """Recupera conocimiento relevante sobre el usuario basado en una consulta."""
        # Obtener memorias relevantes
        memories = self.db.get_relevant_memories(query, limit=5)
        memories_text = "\n".join([f"- {mem['content']}" for mem in memories])
        
        # Obtener entidades relevantes
        profile = self.db.get_user_profile(user_id)
        entities_context = ""
        
        if profile.known_entities:
            all_entity_ids = []
            for ids in profile.known_entities.values():
                all_entity_ids.extend(ids)
            
            entities = list(self.db.entities_coll.find(
                {"entity_id": {"$in": all_entity_ids}},
                sort=[("importance", -1)],
                limit=10
            ))
            
            entities_text = "\n".join([
                f"- {entity['name']} ({entity['type']})"
                for entity in entities
            ])
            
            entities_context = f"\nEntidades importantes:\n{entities_text}"
        
        # Construir el contexto completo
        context = (
            f"Información importante sobre el usuario:\n{memories_text}\n"
            f"{entities_context}"
        )
        
        return context
    
    def generate_long_term_reflection(self, user_id: str) -> str:
        """Genera una reflexión profunda sobre el usuario basada en toda la información disponible."""
        # Obtener información del perfil
        profile_context = self.get_user_profile_context(user_id)
        
        # Obtener insights de actividades
        activity_insights = self.get_activity_insights(user_id, days=30)
        
        # Obtener estadísticas
        stats = self.db.get_user_statistics(user_id)
        
        # Construir el contexto completo
        context = {
            "profile": profile_context,
            "activity_insights": activity_insights,
            "statistics": stats
        }
        
        prompt = (
            "Genera una reflexión profunda y perspicaz sobre el usuario basada en esta información:\n\n"
            f"{context}\n\n"
            "La reflexión debe incluir:\n"
            "1. Una caracterización profunda de su personalidad y motivaciones\n"
            "2. Patrones de comportamiento significativos\n"
            "3. Áreas de desarrollo personal y profesional\n"
            "4. Posibles fortalezas y desafíos\n"
            "5. Una perspectiva holística de quién es esta persona\n\n"
            "Sé detallado pero conciso, evitando generalizaciones y basándote en datos concretos."
        )
        
        reflection = ask_gpt(prompt)
        
        # Guardar la reflexión como memoria del sistema de alta relevancia
        memory_data = {
            "memory_id": str(ObjectId()),
            "content": reflection,
            "type": "user_reflection",
            "relevance": 10,
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.db.add_system_memory(memory_data)
        
        # Actualizar el resumen a largo plazo en el perfil
        profile = self.db.get_user_profile(user_id)
        profile.long_term_summary = reflection
        self.db.update_user_profile(profile)
        
        return reflection
    
    # ======== MÉTODOS DE INTEGRACIÓN PARA EL ORCHESTRATOR ========
    
    def build_orchestrator_context(self, user_id: str, stage: str) -> Dict[str, Any]:
        """Construye el contexto completo para el orquestador en una etapa específica."""
        # Obtener estado actual
        state = self.db.get_state(user_id)
        name = state.get("name", "Desconocido")
        
        # Contexto básico a corto plazo
        st_info = state.get("short_term_info", [])
        last_notes = ". ".join(st_info[-3:]) if st_info else ""
        
        # Añadir información específica según la etapa
        stage_specific_context = self._get_stage_specific_context(user_id, stage)
        
        # Información general del usuario
        user_context = self.get_user_profile_context(user_id)
        
        # Construir el contexto completo
        context = {
            "stage": stage,
            "user_name": name,
            "recent_context": last_notes,
            "user_profile": user_context,
            "stage_specific": stage_specific_context
        }
        
        return context
    
    def _get_stage_specific_context(self, user_id: str, stage: str) -> Dict[str, Any]:
        """Obtiene información específica según la etapa de la conversación."""
        if stage == "ask_profile":
            return self._get_profile_context(user_id)
        elif stage == "ask_last_hour":
            return self._get_last_hour_context(user_id)
        elif stage == "clarifier_last_hour":
            return self._get_clarifier_context(user_id, "past")
        elif stage == "ask_next_hour":
            return self._get_next_hour_context(user_id)
        elif stage == "clarifier_next_hour":
            return self._get_clarifier_context(user_id, "future")
        elif stage == "final":
            return self._get_final_context(user_id)
        else:
            return {}
    
    def _get_profile_context(self, user_id: str) -> Dict[str, Any]:
        """Contexto para la etapa de perfil."""
        profile = self.db.get_user_profile(user_id)
        
        # Determinar qué campos faltan
        missing_fields = []
        gi = profile.general_info
        
        if not gi.name:
            missing_fields.append("nombre")
        if not gi.ocupacion:
            missing_fields.append("ocupación")
        if not gi.gustos:
            missing_fields.append("gustos")
        if not gi.metas:
            missing_fields.append("metas")
        
        return {
            "missing_fields": missing_fields,
            "current_info": {
                "name": gi.name,
                "ocupacion": gi.ocupacion,
                "gustos": gi.gustos,
                "metas": gi.metas
            }
        }
    
    def _get_last_hour_context(self, user_id: str) -> Dict[str, Any]:
        """Contexto para preguntar sobre la última hora."""
        now = datetime.now()
        past_hour = now - timedelta(hours=1)
        
        # Formatear las horas
        time_range = {
            "start": past_hour.strftime("%H:%M"),
            "end": now.strftime("%H:%M")
        }
        
        # Obtener actividades pasadas recientes
        past_activities = self.db.get_recent_activities(
            user_id, 
            time_context="past",
            limit=5
        )
        
        activities_summary = []
        for act in past_activities:
            activities_summary.append({
                "title": act.get("title", ""),
                "category": act.get("category", ""),
                "timestamp": act.get("timestamp", "")
            })
        
        return {
            "time_range": time_range,
            "recent_past_activities": activities_summary,
            "goal": "Obtener información detallada sobre lo que hizo el usuario en la última hora"
        }
    
    def _get_clarifier_context(self, user_id: str, time_context: str) -> Dict[str, Any]:
        """Contexto para etapas de clarificación."""
        # Obtener las actividades más recientes de este contexto
        activities = self.db.get_recent_activities(
            user_id,
            time_context=time_context,
            limit=5
        )
        
        # Obtener historial de clarificación
        state = self.db.get_state(user_id)
        clarifier_history = state.get("clarifier_history", [])[-3:]
        
        return {
            "time_context": time_context,
            "activities": activities,
            "clarifier_history": clarifier_history,
            "goal": f"Profundizar en detalles sobre las actividades {time_context}"
        }
    
    def _get_next_hour_context(self, user_id: str) -> Dict[str, Any]:
        """Contexto para preguntar sobre la próxima hora."""
        now = datetime.now()
        next_hour = now + timedelta(hours=1)
        
        # Formatear las horas
        time_range = {
            "start": now.strftime("%H:%M"),
            "end": next_hour.strftime("%H:%M")
        }
        
        # Obtener actividades futuras ya mencionadas
        future_activities = self.db.get_recent_activities(
            user_id, 
            time_context="future",
            limit=5
        )
        
        activities_summary = []
        for act in future_activities:
            activities_summary.append({
                "title": act.get("title", ""),
                "category": act.get("category", ""),
                "timestamp": act.get("timestamp", "")
            })
        
        return {
            "time_range": time_range,
            "known_future_activities": activities_summary,
            "goal": "Obtener información detallada sobre lo que planea hacer el usuario en la próxima hora"
        }
    
    def _get_final_context(self, user_id: str) -> Dict[str, Any]:
        """Contexto para la etapa final."""
        # Obtener un resumen de lo recopilado en esta conversación
        state = self.db.get_state(user_id)
        
        # Actividades pasadas recopiladas
        past_activities = state.get("activities_last_hour", [])
        
        # Actividades futuras recopiladas
        future_activities = state.get("activities_next_hour", [])
        
        # Generar un pequeño análisis
        analysis = "No se ha generado un análisis aún."
        if past_activities or future_activities:
            analysis = self._generate_quick_analysis(user_id, past_activities, future_activities)
        
        return {
            "past_activities_count": len(past_activities),
            "future_activities_count": len(future_activities),
            "analysis": analysis,
            "goal": "Cerrar la conversación y preparar para la próxima interacción"
        }
    
    def _generate_quick_analysis(self, user_id: str, past_activities: List[Dict[str, Any]], future_activities: List[Dict[str, Any]]) -> str:
        """Genera un análisis rápido de las actividades recopiladas."""
        prompt = (
            f"El usuario ha mencionado {len(past_activities)} actividades pasadas y {len(future_activities)} actividades futuras. "
            "Genera un breve análisis (2-3 frases) sobre qué podría indicar esto sobre su día y estado actual."
        )
        
        analysis = ask_gpt(prompt)
        return analysis