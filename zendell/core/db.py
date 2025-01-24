# zendell/core/db.py
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from bson.objectid import ObjectId

MONGO_URL = "mongodb://root:rootpass@localhost:27017/?authSource=admin"

class MongoDBManager:
    def __init__(self, uri: str = MONGO_URL, db_name: str = "zendell_db"):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]

        # Colecciones
        self.users_coll = self.db["users"]
        self.user_state_coll = self.db["user_states"]
        self.activities_coll = self.db["activities"]
        self.goals_coll = self.db["goals"]
        self.conversations_coll = self.db["conversation_logs"]  # Para guardar cada bloque de mensajes

    def get_state(self, user_id: str) -> Dict[str, Any]:
        """
        Recupera el documento user_state de la colección 'user_states'.
        Si no existe, crea un estado inicial y lo retorna.
        """
        doc = self.user_state_coll.find_one({"user_id": user_id})

        # Si el usuario no tiene estado, creamos uno nuevo por defecto
        if not doc:
            initial_state = {
                "user_id": user_id,
                "name": "Desconocido",
                "last_interaction_time": "",
                "daily_interaction_count": 0,
                "last_interaction_date": "",
                "short_term_info": [],
                "general_info": {
                    "metas": "",
                    "gustos": "",
                    "ocupacion": "",
                    # Puedes agregar más campos
                }
            }
            self.user_state_coll.insert_one(initial_state)
            return initial_state

        # Retornamos un dict con campos necesarios, mergeando defaults
        return {
            "user_id": doc["user_id"],
            "name": doc.get("name", "Desconocido"),
            "last_interaction_time": doc.get("last_interaction_time", ""),
            "daily_interaction_count": doc.get("daily_interaction_count", 0),
            "last_interaction_date": doc.get("last_interaction_date", ""),
            "short_term_info": doc.get("short_term_info", []),
            "general_info": doc.get("general_info", {})
        }

    def save_state(self, user_id: str, state: Dict[str, Any]) -> None:
        """
        Inserta o actualiza un user_state en 'user_states'.
        Se asegura de mantener la estructura base.
        """
        query = {"user_id": user_id}
        update_data = {
            "user_id": user_id,
            "name": state.get("name", "Desconocido"),
            "last_interaction_time": state.get("last_interaction_time", ""),
            "daily_interaction_count": state.get("daily_interaction_count", 0),
            "last_interaction_date": state.get("last_interaction_date", ""),
            "short_term_info": state.get("short_term_info", []),
            "general_info": state.get("general_info", {})
        }

        self.user_state_coll.update_one(query, {"$set": update_data}, upsert=True)

    def add_activity(self, user_id: str, activity_data: Dict[str, Any]):
        """
        Inserta una actividad en 'activities'.
        """
        activity_data["user_id"] = user_id
        activity_data["timestamp"] = datetime.utcnow().isoformat()
        activity_data["activity_id"] = str(ObjectId())
        self.activities_coll.insert_one(activity_data)

    def save_conversation_message(self, user_id: str, role: str, content: str,
                                  extra_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Guarda un nuevo mensaje (user o assistant) en la colección 'conversation_logs'.
        - Crea un nuevo 'conversation_id' si no hay uno activo
          o depende de cómo queramos agrupar las conversaciones.
        - 'extra_data' puede contener el tono, intención, etc.
        """
        timestamp_str = datetime.utcnow().isoformat()

        # Aquí podrías decidir si cada mensaje es un doc aparte o agruparlos.
        # Por ejemplo, hacemos un doc por mensaje simple:
        message_doc = {
            "user_id": user_id,
            "role": role,  # "user" o "assistant"
            "content": content,
            "timestamp": timestamp_str,
        }

        # Adjuntamos datos extra (tono, intención, etc.) si viene
        if extra_data:
            message_doc.update(extra_data)

        self.conversations_coll.insert_one(message_doc)

    def get_user_conversation(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Devuelve los últimos 'limit' mensajes guardados para un user_id.
        """
        cursor = self.conversations_coll.find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
        return list(cursor)[::-1]  # invertimos para que queden en orden cronológico
