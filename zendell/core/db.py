# zendell/core/db.py

from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple, Set
from bson.objectid import ObjectId
from pymongo import MongoClient, ASCENDING, DESCENDING
from core.utils import get_timestamp
from zendell.services.llm_provider import ask_gpt
from zendell.core.db_models import (
    UserProfile, UserState, Activity, ConversationMessage, 
    Memory, PersonEntity, PlaceEntity, ConceptEntity, 
    EntityReference, ActivityMention, SystemMemory,
    GeneralInfo, ClarificationQA
)

MONGO_URL = "mongodb://root:rootpass@localhost:27017/?authSource=admin"

class MongoDBManager:
    def __init__(self, uri: str = MONGO_URL, db_name: str = "zendell_db"):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        
        # Colecciones principales
        self.user_profiles_coll = self.db["user_profiles"]
        self.user_states_coll = self.db["user_states"]
        self.activities_coll = self.db["activities"]
        self.conversations_coll = self.db["conversations"]
        self.entities_coll = self.db["entities"]
        self.memories_coll = self.db["system_memories"]
        
        # Inicializar índices
        self._initialize_indices()
    
    def _initialize_indices(self):
        """Inicializa los índices necesarios en las colecciones."""
        # User profiles
        self.user_profiles_coll.create_index([("user_id", ASCENDING)], unique=True)
        
        # User states
        self.user_states_coll.create_index([("user_id", ASCENDING)], unique=True)
        
        # Activities
        self.activities_coll.create_index([("user_id", ASCENDING), ("timestamp", DESCENDING)])
        self.activities_coll.create_index([("activity_id", ASCENDING)], unique=True)
        self.activities_coll.create_index([("user_id", ASCENDING), ("time_context", ASCENDING)])
        self.activities_coll.create_index([("user_id", ASCENDING), ("category", ASCENDING)])
        
        # Conversations
        self.conversations_coll.create_index([("user_id", ASCENDING), ("timestamp", DESCENDING)])
        self.conversations_coll.create_index([("user_id", ASCENDING), ("conversation_stage", ASCENDING)])
        
        # Entities
        self.entities_coll.create_index([("entity_id", ASCENDING)], unique=True)
        self.entities_coll.create_index([("name", ASCENDING), ("type", ASCENDING)])
        
        # Memories
        self.memories_coll.create_index([("memory_id", ASCENDING)], unique=True)
        self.memories_coll.create_index([("type", ASCENDING), ("relevance", DESCENDING)])

    # ======== MÉTODOS PARA PERFILES DE USUARIO ========
    
    def get_user_profile(self, user_id: str) -> UserProfile:
        """Obtiene el perfil completo del usuario."""
        doc = self.user_profiles_coll.find_one({"user_id": user_id})
        if not doc:
            # Crear un perfil nuevo
            profile = UserProfile(user_id=user_id)
            self.user_profiles_coll.insert_one(profile.to_dict())
            return profile
        
        # Convertir de diccionario a objeto UserProfile
        return UserProfile.from_dict(doc)
    
    def update_user_profile(self, profile: UserProfile) -> None:
        """Actualiza el perfil completo del usuario."""
        profile.last_updated = datetime.utcnow().isoformat()
        self.user_profiles_coll.update_one(
            {"user_id": profile.user_id},
            {"$set": profile.to_dict()},
            upsert=True
        )
    
    def update_general_info(self, user_id: str, field_name: str, value: Any) -> None:
        """Actualiza un campo específico de la información general."""
        profile = self.get_user_profile(user_id)
        
        # Si no existe general_info, créalo
        if not hasattr(profile, 'general_info') or profile.general_info is None:
            profile.general_info = GeneralInfo()
        
        # Actualizar el campo si existe
        if hasattr(profile.general_info, field_name):
            setattr(profile.general_info, field_name, value)
            self.update_user_profile(profile)
    
    def add_entity_to_user_profile(self, user_id: str, entity_type: str, entity_id: str) -> None:
        """Añade una referencia a una entidad en el perfil del usuario."""
        profile = self.get_user_profile(user_id)
        
        # Inicializar el diccionario si no existe
        if not profile.known_entities:
            profile.known_entities = {}
        
        # Inicializar la lista si no existe
        if entity_type not in profile.known_entities:
            profile.known_entities[entity_type] = []
        
        # Añadir el ID de la entidad si no está ya
        if entity_id not in profile.known_entities[entity_type]:
            profile.known_entities[entity_type].append(entity_id)
            self.update_user_profile(profile)
    
    def extract_and_update_user_info(self, user_id: str, message: str) -> Dict[str, Any]:
        """Extrae información del usuario del mensaje y actualiza su perfil."""
        print(f"{get_timestamp()}",f"[DB] Extrayendo información del usuario del mensaje: '{message[:50]}...'")
        
        prompt = (
            "Analiza el siguiente mensaje y extrae datos personales relevantes sobre el usuario. "
            "Devuelve un JSON con los siguientes campos (deja vacío si no hay información):\n"
            "{\n"
            "  \"name\": \"\",\n"
            "  \"ocupacion\": \"\",\n"
            "  \"gustos\": \"\",\n"
            "  \"metas\": \"\"\n"
            "}\n\n"
            f"Mensaje: {message}"
        )
        
        response = ask_gpt(prompt)
        print(f"{get_timestamp()}",f"[DB] Respuesta de extracción de info de usuario: '{response[:100]}...'")
        
        try:
            import json
            import re
            
            # Buscar patrón JSON en la respuesta
            json_pattern = r'(\{.*\})'
            matches = re.search(json_pattern, response, re.DOTALL)
            
            if matches:
                json_str = matches.group(1)
                extracted_info = json.loads(json_str)
            else:
                # Intentar limpiar y parsear
                cleaned_response = re.sub(r'^[^{]*', '', response)
                cleaned_response = re.sub(r'[^}]*$', '', cleaned_response)
                
                if cleaned_response:
                    extracted_info = json.loads(cleaned_response)
                else:
                    print(f"{get_timestamp()}","[DB] No se pudo extraer JSON de información de usuario, devolviendo diccionario vacío")
                    return {}
            
            # Mostrar la información extraída
            print(f"{get_timestamp()}",f"[DB] Información extraída del usuario: {extracted_info}")
            
            # Actualizar el estado del usuario directamente
            state = self.get_state(user_id)
            
            # Crear general_info si no existe
            if "general_info" not in state:
                state["general_info"] = {}
            
            # Actualizar el nombre en el estado directamente
            if extracted_info.get("name"):
                state["name"] = extracted_info["name"]
                print(f"{get_timestamp()}",f"[DB] Nombre en el estado actualizado a: {extracted_info['name']}")
            
            # Actualizar los campos en general_info
            for field in ["name", "ocupacion", "gustos", "metas"]:
                if field in extracted_info and extracted_info[field]:
                    state["general_info"][field] = extracted_info[field]
                    print(f"{get_timestamp()}",f"[DB] Campo '{field}' actualizado en general_info: {extracted_info[field]}")
            
            # Guardar el estado actualizado
            self.save_state(user_id, state)
            
            # Actualizar también el perfil si existe
            try:
                profile = self.get_user_profile(user_id)
                for field, value in extracted_info.items():
                    if value and hasattr(profile.general_info, field):
                        setattr(profile.general_info, field, value)
                self.update_user_profile(profile)
            except Exception as e:
                print(f"{get_timestamp()}",f"[DB] Error al actualizar perfil: {e}")
            
            return extracted_info
            
        except Exception as e:
            print(f"{get_timestamp()}",f"[DB] Error al procesar la información extraída: {e}")
            return {}
        
    def generate_user_summary(self, user_id: str) -> str:
        """Genera un resumen del perfil del usuario."""
        profile = self.get_user_profile(user_id)
        
        # Obtener actividades recientes
        recent_activities = list(self.activities_coll.find(
            {"user_id": user_id},
            sort=[("timestamp", DESCENDING)],
            limit=10
        ))
        
        # Obtener entidades más mencionadas
        entities = list(self.entities_coll.find(
            {"entity_id": {"$in": sum(profile.known_entities.values(), [])}},
            sort=[("mention_count", DESCENDING)],
            limit=10
        ))
        
        # Crear contexto para el resumen
        context = {
            "profile": profile.to_dict(),
            "recent_activities": recent_activities,
            "important_entities": entities
        }
        
        prompt = (
            "Genera un resumen detallado y perspicaz del usuario basado en la siguiente información:\n\n"
            f"{context}\n\n"
            "El resumen debe incluir:\n"
            "1. Personalidad, preferencias y patrones observados\n"
            "2. Metas importantes y motivaciones\n"
            "3. Relaciones significativas\n"
            "4. Rutinas habituales\n"
            "5. Áreas de interés principal\n\n"
            "Redacta el resumen como un análisis profundo que capture la esencia de quién es este usuario, "
            "sus prioridades y lo que parece valorar más."
        )
        
        summary = ask_gpt(prompt)
        
        # Actualizar el perfil con el nuevo resumen
        profile.long_term_summary = summary
        self.update_user_profile(profile)
        
        return summary
    
    # ======== MÉTODOS PARA ESTADOS DE USUARIO ========
    
    def get_state(self, user_id: str) -> Dict[str, Any]:
        """Obtiene el estado actual del usuario."""
        print(f"{get_timestamp()}",f"[DB] Obteniendo estado para user_id: {user_id}")
        
        try:
            doc = self.user_states_coll.find_one({"user_id": user_id})
            
            if not doc:
                print(f"{get_timestamp()}",f"[DB] No se encontró estado para user_id: {user_id}, creando uno nuevo")
                
                # Crear un estado inicial
                initial_state = {
                    "user_id": user_id,
                    "name": "Desconocido",
                    "last_interaction_time": "",
                    "daily_interaction_count": 0,
                    "last_interaction_date": "",
                    "conversation_stage": "initial",
                    "short_term_info": [],
                    "general_info": {}
                }
                
                # Insertar el nuevo estado
                self.user_states_coll.insert_one(initial_state)
                return initial_state
            
            # Verificar campos esenciales y añadirlos si faltan
            if "name" not in doc:
                doc["name"] = "Desconocido"
            
            if "conversation_stage" not in doc:
                doc["conversation_stage"] = "initial"
            
            if "short_term_info" not in doc:
                doc["short_term_info"] = []
            
            if "general_info" not in doc:
                doc["general_info"] = {}
            
            # Guardar el estado con los campos añadidos si es necesario
            if any(field not in doc for field in ["name", "conversation_stage", "short_term_info", "general_info"]):
                self.user_states_coll.update_one({"user_id": user_id}, {"$set": doc})
                print(f"{get_timestamp()}",f"[DB] Estado actualizado con campos faltantes para user_id: {user_id}")
            
            print(f"{get_timestamp()}",f"[DB] Estado recuperado correctamente para user_id: {user_id}")
            return doc
        
        except Exception as e:
            print(f"{get_timestamp()}",f"[DB] Error al obtener estado para user_id {user_id}: {e}")
            # Devolver un estado por defecto en caso de error
            return {
                "user_id": user_id,
                "name": "Desconocido",
                "last_interaction_time": "",
                "daily_interaction_count": 0,
                "last_interaction_date": "",
                "conversation_stage": "initial",
                "short_term_info": [],
                "general_info": {}
            }
    
    def save_state(self, user_id: str, state: Dict[str, Any]) -> None:
        """Guarda el estado actual del usuario."""
        query = {"user_id": user_id}
        self.user_states_coll.update_one(query, {"$set": state}, upsert=True)
    
    def update_conversation_stage(self, user_id: str, stage: str) -> None:
        """Actualiza la etapa de conversación del usuario."""
        self.user_states_coll.update_one(
            {"user_id": user_id},
            {"$set": {"conversation_stage": stage}}
        )
    
    def add_to_short_term_info(self, user_id: str, info: str) -> None:
        """Añade información al contexto de corto plazo."""
        self.user_states_coll.update_one(
            {"user_id": user_id},
            {
                "$push": {
                    "short_term_info": {
                        "$each": [info],
                        "$slice": -20  # Mantener solo los últimos 20 elementos
                    }
                }
            }
        )
    
    # ======== MÉTODOS PARA ACTIVIDADES ========
    
    def add_activity(self, user_id: str, activity_data: Dict[str, Any]) -> str:
        """Añade una actividad y devuelve su ID."""
        # Asegurar que tiene un ID único
        if "activity_id" not in activity_data:
            activity_data["activity_id"] = str(ObjectId())
        
        # Añadir user_id y timestamp si no existen
        activity_data["user_id"] = user_id
        if "timestamp" not in activity_data:
            activity_data["timestamp"] = datetime.utcnow().isoformat()
        
        # Insertar la actividad
        self.activities_coll.insert_one(activity_data)
        
        # Actualizar el estado para mantener referencia a actividades recientes
        state = self.get_state(user_id)
        context_key = "activities_last_hour" if activity_data.get("time_context") == "past" else "activities_next_hour"
        if context_key not in state:
            state[context_key] = []
        
        activity_reference = {
            "timestamp": activity_data["timestamp"],
            "activity_id": activity_data["activity_id"],
            "title": activity_data.get("title", ""),
            "category": activity_data.get("category", "")
        }
        
        state.setdefault(context_key, []).append(activity_reference)
        
        # Mantener solo las últimas 10 actividades
        if len(state[context_key]) > 10:
            state[context_key] = state[context_key][-10:]
        
        self.save_state(user_id, state)
        
        return activity_data["activity_id"]
    
    def get_activity(self, activity_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene una actividad por su ID."""
        return self.activities_coll.find_one({"activity_id": activity_id})
    
    def update_activity(self, activity_id: str, updates: Dict[str, Any]) -> None:
        """Actualiza una actividad existente."""
        self.activities_coll.update_one(
            {"activity_id": activity_id},
            {"$set": updates}
        )
    
    def add_clarification_to_activity(self, activity_id: str, question: str, answer: str) -> None:
        """Añade una pregunta y respuesta de clarificación a una actividad."""
        clarification = {
            "question": question,
            "answer": answer,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.activities_coll.update_one(
            {"activity_id": activity_id},
            {"$push": {"clarifier_responses": clarification}}
        )
    
    def analyze_activities(self, user_id: str, time_context: str = None, limit: int = 10) -> str:
        """Analiza las actividades recientes del usuario."""
        query = {"user_id": user_id}
        if time_context:
            query["time_context"] = time_context
        
        activities = list(self.activities_coll.find(
            query,
            sort=[("timestamp", DESCENDING)],
            limit=limit
        ))
        
        if not activities:
            return "No hay actividades recientes para analizar."
        
        # Preparar el análisis con LLM
        prompt = (
            f"Analiza las siguientes {len(activities)} actividades del usuario:\n\n"
            f"{activities}\n\n"
            "Proporciona un análisis detallado que incluya:\n"
            "1. Patrones observados en las actividades\n"
            "2. Posibles intereses y prioridades\n"
            "3. Estado emocional inferido\n"
            "4. Recomendaciones para optimizar su tiempo\n"
            "5. Conclusiones generales sobre su estilo de vida\n\n"
            "Basa tu análisis en datos concretos de las actividades."
        )
        
        analysis = ask_gpt(prompt)
        
        # Guardar el análisis como una memoria del sistema
        memory_id = str(ObjectId())
        memory = SystemMemory(
            memory_id=memory_id,
            content=analysis,
            type="activity_analysis",
            relevance=8,
            related_activities=[
                ActivityMention(activity_id=a["activity_id"], context="análisis de actividades")
                for a in activities
            ]
        )
        
        self.memories_coll.insert_one(memory.to_dict())
        
        return analysis
    
    def get_recent_activities(self, user_id: str, time_context: Optional[str] = None, categories: Optional[List[str]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtiene actividades recientes del usuario con filtros opcionales."""
        query = {"user_id": user_id}
        
        if time_context:
            query["time_context"] = time_context
            
        if categories:
            query["category"] = {"$in": categories}
            
        activities = list(self.activities_coll.find(
            query,
            sort=[("timestamp", DESCENDING)],
            limit=limit
        ))
        
        return activities
    
    # ======== MÉTODOS PARA CONVERSACIONES ========
    
    def save_conversation_message(self, user_id: str, role: str, content: str, extra_data: Optional[Dict[str, Any]] = None) -> str:
        """Guarda un mensaje de la conversación y devuelve su ID."""
        timestamp_str = datetime.utcnow().isoformat()
        message_id = str(ObjectId())
        
        message_doc = {
            "message_id": message_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "timestamp": timestamp_str
        }
        
        if extra_data:
            message_doc.update(extra_data)
        
        # Extraer entidades y actividades mencionadas
        if role == "user" and content:
            message_doc["entities_extracted"] = self._extract_entities_from_message(user_id, content)
        
        self.conversations_coll.insert_one(message_doc)
        
        # Actualizar el contexto de corto plazo
        short_info = f"[{role.upper()}] {content[:100]}" + ("..." if len(content) > 100 else "")
        self.add_to_short_term_info(user_id, short_info)
        
        return message_id
    
    def get_user_conversation(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Obtiene los mensajes recientes de un usuario."""
        cursor = self.conversations_coll.find(
            {"user_id": user_id},
            sort=[("timestamp", DESCENDING)],
            limit=limit
        )
        return list(cursor)[::-1]  # Invertir para orden cronológico
    
    def get_conversation_by_stage(self, user_id: str, stage: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Obtiene mensajes de una etapa específica de la conversación."""
        query = {
            "user_id": user_id,
            "$or": [
                {"conversation_stage": stage},
                {"extra_data.step": stage}
            ]
        }
        
        cursor = self.conversations_coll.find(
            query,
            sort=[("timestamp", DESCENDING)],
            limit=limit
        )
        
        return list(cursor)
    
    def analyze_conversation(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """Analiza la conversación reciente para extraer insights."""
        messages = self.get_user_conversation(user_id, limit)
        
        if not messages:
            return {"mood": "neutral", "topics": [], "insights": []}
        
        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in messages
        ])
        
        prompt = (
            "Analiza esta conversación reciente y extrae lo siguiente:\n\n"
            f"{conversation_text}\n\n"
            "Proporciona la siguiente información en formato JSON:\n"
            "{\n"
            "  \"mood\": \"estado de ánimo inferido del usuario\",\n"
            "  \"topics\": [\"tema principal 1\", \"tema principal 2\", ...],\n"
            "  \"concerns\": [\"preocupación 1\", \"preocupación 2\", ...],\n"
            "  \"insights\": [\"insight 1 sobre el usuario\", \"insight 2\", ...],\n"
            "  \"implicit_needs\": [\"necesidad implícita 1\", \"necesidad implícita 2\", ...]\n"
            "}\n\n"
            "Basa tu análisis en patrones sutiles, tono, elección de palabras y contexto."
        )
        
        response = ask_gpt(prompt)
        
        try:
            import json
            analysis = json.loads(response)
            
            # Actualizar el estado del usuario con el estado de ánimo
            self.user_states_coll.update_one(
                {"user_id": user_id},
                {"$set": {"mood": analysis.get("mood", "neutral")}}
            )
            
            # Guardar los insights como memorias del sistema
            for insight in analysis.get("insights", []):
                memory_id = str(ObjectId())
                memory = SystemMemory(
                    memory_id=memory_id,
                    content=insight,
                    type="conversation_insight",
                    relevance=7
                )
                self.memories_coll.insert_one(memory.to_dict())
            
            return analysis
            
        except Exception as e:
            print(f"{get_timestamp()}",f"Error al analizar la conversación: {e}")
            return {"mood": "neutral", "topics": [], "insights": []}
    
    # ======== MÉTODOS PARA ENTIDADES ========
    
    def _extract_entities_from_message(self, user_id: str, message: str) -> List[Dict[str, Any]]:
        """Extrae entidades (personas, lugares, conceptos) de un mensaje."""
        print(f"{get_timestamp()}",f"[DB] Extrayendo entidades del mensaje: '{message[:50]}...'")
        
        prompt = (
            "Extrae entidades mencionadas en el siguiente mensaje. Devuelve un JSON con esta estructura:\n"
            "{\n"
            "  \"entities\": [\n"
            "    {\"name\": \"Juan Pérez\", \"type\": \"person\", \"context\": \"amigo mencionado\"},\n"
            "    {\"name\": \"Café Central\", \"type\": \"place\", \"context\": \"lugar visitado\"},\n"
            "    {\"name\": \"programación\", \"type\": \"concept\", \"context\": \"interés mencionado\"}\n"
            "  ]\n"
            "}\n\n"
            f"Mensaje: {message}\n\n"
            "IMPORTANTE: Responde ÚNICAMENTE con un JSON válido, sin texto adicional."
        )
        
        response = ask_gpt(prompt)
        print(f"{get_timestamp()}",f"[DB] Respuesta del LLM (primeros 100 caracteres): '{response[:100]}...'")
        
        entities_found = []
        
        try:
            import json
            import re
            
            # Limpiar la respuesta para asegurarnos de que es JSON válido
            # Buscar el patrón de JSON en la respuesta
            json_pattern = r'(\{.*\})'
            matches = re.search(json_pattern, response, re.DOTALL)
            
            if matches:
                json_str = matches.group(1)
                print(f"{get_timestamp()}",f"[DB] JSON extraído: '{json_str[:50]}...'")
                extracted = json.loads(json_str)
            else:
                # Intentar limpiar eliminando texto antes y después de llaves
                cleaned_response = re.sub(r'^[^{]*', '', response)
                cleaned_response = re.sub(r'[^}]*$', '', cleaned_response)
                print(f"{get_timestamp()}",f"[DB] Respuesta limpiada: '{cleaned_response[:50]}...'")
                
                if cleaned_response:
                    extracted = json.loads(cleaned_response)
                else:
                    print(f"{get_timestamp()}","[DB] No se pudo extraer JSON, devolviendo lista vacía")
                    return []
            
            # Procesar las entidades encontradas
            for entity in extracted.get("entities", []):
                entity_name = entity.get("name", "").strip()
                entity_type = entity.get("type", "").strip()
                entity_context = entity.get("context", "").strip()
                
                if not entity_name or not entity_type:
                    continue
                
                print(f"{get_timestamp()}",f"[DB] Entidad encontrada: {entity_name} ({entity_type})")
                
                # Generar un ID único para la entidad
                entity_id = str(ObjectId())
                
                # Crear un diccionario simple en lugar de usar dataclass
                entity_data = {
                    "entity_id": entity_id,
                    "name": entity_name,
                    "type": entity_type,
                    "context": entity_context,
                    "first_mentioned": datetime.utcnow().isoformat(),
                    "last_mentioned": datetime.utcnow().isoformat(),
                    "mention_count": 1,
                    "importance": 5
                }
                
                # Verificar si la entidad ya existe
                existing = self.entities_coll.find_one({
                    "name": entity_name,
                    "type": entity_type
                })
                
                if existing:
                    # Actualizar entidad existente
                    entity_id = existing["entity_id"]
                    self.entities_coll.update_one(
                        {"entity_id": entity_id},
                        {
                            "$set": {"last_mentioned": datetime.utcnow().isoformat()},
                            "$inc": {"mention_count": 1}
                        }
                    )
                    print(f"{get_timestamp()}",f"[DB] Entidad actualizada: {entity_id}")
                else:
                    # Insertar la nueva entidad directamente como diccionario
                    self.entities_coll.insert_one(entity_data)
                    print(f"{get_timestamp()}",f"[DB] Nueva entidad creada: {entity_id}")
                
                # Añadir entidad al perfil del usuario
                try:
                    self.add_entity_to_user_profile(user_id, entity_type, entity_id)
                except Exception as e:
                    print(f"{get_timestamp()}",f"[DB] Error al añadir entidad al perfil del usuario: {e}")
                
                # Añadir a la lista de entidades encontradas
                entities_found.append({
                    "entity_id": entity_id,
                    "name": entity_name,
                    "type": entity_type,
                    "context": entity_context
                })
            
            return entities_found
                
        except Exception as e:
            print(f"{get_timestamp()}",f"[DB] Error al extraer entidades: {e}")
            # Devolvemos una lista vacía para no bloquear el flujo
            return []
        
    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene una entidad por su ID."""
        return self.entities_coll.find_one({"entity_id": entity_id})
    
    def get_entities_by_type(self, user_id: str, entity_type: str) -> List[Dict[str, Any]]:
        """Obtiene entidades conocidas por el usuario de un tipo específico."""
        profile = self.get_user_profile(user_id)
        entity_ids = profile.known_entities.get(entity_type, [])
        
        if not entity_ids:
            return []
        
        entities = list(self.entities_coll.find(
            {"entity_id": {"$in": entity_ids}},
            sort=[("importance", DESCENDING)]
        ))
        
        return entities
    
    def update_entity(self, entity_id: str, updates: Dict[str, Any]) -> None:
        """Actualiza una entidad existente."""
        self.entities_coll.update_one(
            {"entity_id": entity_id},
            {"$set": updates}
        )
    
    # ======== MÉTODOS PARA MEMORIA DEL SISTEMA ========
    
    def add_system_memory(self, memory_data: Dict[str, Any]) -> str:
        """Añade una memoria del sistema y devuelve su ID."""
        if "memory_id" not in memory_data:
            memory_data["memory_id"] = str(ObjectId())
        
        if "created_at" not in memory_data:
            memory_data["created_at"] = datetime.utcnow().isoformat()
        
        if "last_accessed" not in memory_data:
            memory_data["last_accessed"] = memory_data["created_at"]
        
        self.memories_coll.insert_one(memory_data)
        return memory_data["memory_id"]
    
    def get_relevant_memories(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Obtiene memorias relevantes para un contexto específico."""
        # Aquí se podría implementar una búsqueda semántica más avanzada
        # Por ahora, hacemos una búsqueda simple por palabras clave
        keywords = [word.lower() for word in query_text.split() if len(word) > 3]
        
        # Construir una consulta de búsqueda de texto
        search_conditions = []
        for keyword in keywords:
            search_conditions.append({"content": {"$regex": keyword, "$options": "i"}})
        
        if not search_conditions:
            # Si no hay palabras clave válidas, devolver las memorias más relevantes
            return list(self.memories_coll.find(
                sort=[("relevance", DESCENDING)],
                limit=limit
            ))
        
        # Buscar memorias que coincidan con al menos una palabra clave
        memories = list(self.memories_coll.find(
            {"$or": search_conditions},
            sort=[("relevance", DESCENDING)],
            limit=limit
        ))
        
        # Actualizar el contador de accesos
        for memory in memories:
            self.memories_coll.update_one(
                {"memory_id": memory["memory_id"]},
                {
                    "$set": {"last_accessed": datetime.utcnow().isoformat()},
                    "$inc": {"access_count": 1}
                }
            )
        
        return memories
    
    def generate_system_insights(self, user_id: str) -> List[str]:
        """Genera insights del sistema basados en datos recopilados."""
        # Obtener datos relevantes
        profile = self.get_user_profile(user_id)
        recent_activities = self.get_recent_activities(user_id, limit=20)
        recent_conversations = self.get_user_conversation(user_id, limit=20)
        
        # Crear contexto para el análisis
        context = {
            "profile_summary": profile.long_term_summary,
            "general_info": profile.general_info.to_dict(),
            "recent_activities_count": len(recent_activities),
            "recent_conversations_count": len(recent_conversations),
            "personality_traits": profile.personality_traits,
            "common_categories": self._get_common_activity_categories(user_id)
        }
        
        prompt = (
            "Genera 3-5 insights profundos sobre el usuario basados en este contexto:\n\n"
            f"{context}\n\n"
            "Los insights deben ser observaciones no obvias que revelen patrones, motivaciones "
            "o comportamientos importantes. Cada insight debe incluir:\n"
            "1. La observación principal\n"
            "2. Evidencia que respalda esa observación\n"
            "3. Posibles implicaciones para el usuario\n\n"
            "Formato: Lista de insights separados por saltos de línea dobles."
        )
        
        response = ask_gpt(prompt)
        insights = [insight.strip() for insight in response.split("\n\n") if insight.strip()]
        
        # Guardar los insights como memorias del sistema
        for insight in insights:
            memory_id = str(ObjectId())
            memory = SystemMemory(
                memory_id=memory_id,
                content=insight,
                type="system_insight",
                relevance=9
            )
            self.memories_coll.insert_one(memory.to_dict())
        
        return insights
    
    def _get_common_activity_categories(self, user_id: str) -> Dict[str, int]:
        """Obtiene las categorías de actividad más comunes para un usuario."""
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]
        
        results = list(self.activities_coll.aggregate(pipeline))
        return {result["_id"]: result["count"] for result in results if result["_id"]}
    
    # ======== MÉTODOS DE CONSULTA AVANZADA ========
    
    def find_related_activities(self, entity_id: str) -> List[Dict[str, Any]]:
        """Encuentra actividades relacionadas con una entidad específica."""
        entity = self.get_entity(entity_id)
        if not entity:
            return []
        
        # Buscar actividades que mencionen esta entidad
        activities = list(self.activities_coll.find(
            {"entities.entity_id": entity_id},
            sort=[("timestamp", DESCENDING)]
        ))
        
        return activities
    
    def get_long_term_context(self, user_id: str) -> Dict[str, Any]:
        """Obtiene un contexto completo a largo plazo para el usuario."""
        profile = self.get_user_profile(user_id)
        
        # Obtener entidades importantes
        important_entities = []
        for entity_type, entity_ids in profile.known_entities.items():
            entities = list(self.entities_coll.find(
                {"entity_id": {"$in": entity_ids}},
                sort=[("importance", DESCENDING)],
                limit=5
            ))
            important_entities.extend(entities)
        
        # Obtener actividades recurrentes
        recurring_activities = self._get_recurring_activities(user_id)
        
        # Obtener insights del sistema
        system_insights = list(self.memories_coll.find(
            {"type": "system_insight"},
            sort=[("relevance", DESCENDING)],
            limit=5
        ))
        
        return {
            "profile": profile.to_dict(),
            "important_entities": important_entities,
            "recurring_activities": recurring_activities,
            "system_insights": system_insights
        }
    
    def _get_recurring_activities(self, user_id: str) -> List[Dict[str, Any]]:
        """Identifica actividades recurrentes del usuario."""
        # Agrupar actividades por título y contar ocurrencias
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": "$title",
                "count": {"$sum": 1},
                "category": {"$first": "$category"},
                "first_occurrence": {"$min": "$timestamp"},
                "last_occurrence": {"$max": "$timestamp"}
            }},
            {"$match": {"count": {"$gt": 1}}},  # Más de una ocurrencia
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        
        results = list(self.activities_coll.aggregate(pipeline))
        return results
    
    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Obtiene estadísticas sobre la interacción con el usuario."""
        total_activities = self.activities_coll.count_documents({"user_id": user_id})
        total_conversations = self.conversations_coll.count_documents({"user_id": user_id})
        total_entities = sum(len(entity_ids) for entity_ids in self.get_user_profile(user_id).known_entities.values())
        
        first_interaction = self.conversations_coll.find_one(
            {"user_id": user_id},
            sort=[("timestamp", ASCENDING)]
        )
        
        last_interaction = self.conversations_coll.find_one(
            {"user_id": user_id},
            sort=[("timestamp", DESCENDING)]
        )
        
        # Calcular la duración de la relación
        first_date = first_interaction["timestamp"] if first_interaction else datetime.utcnow().isoformat()
        last_date = last_interaction["timestamp"] if last_interaction else datetime.utcnow().isoformat()
        
        try:
            first_datetime = datetime.fromisoformat(first_date)
            last_datetime = datetime.fromisoformat(last_date)
            relationship_days = (last_datetime - first_datetime).days
        except ValueError:
            relationship_days = 0
        
        return {
            "total_activities": total_activities,
            "total_conversations": total_conversations,
            "total_entities_known": total_entities,
            "first_interaction": first_date,
            "last_interaction": last_date,
            "days_of_relationship": relationship_days
        }