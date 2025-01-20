# core/db.py
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from bson.objectid import ObjectId

# Nota: Si vas a usar Docker con la URI:
MONGO_URL = "mongodb://root:rootpass@localhost:27017/?authSource=admin"
# Ajusta usuario y pass según tu docker-compose

class MongoDBManager:
    def __init__(self, uri: str = MONGO_URL, db_name: str = "zendell_db"):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]

        # Ejemplo de colecciones:
        self.users_coll = self.db["users"]
        self.user_state_coll = self.db["user_states"]
        self.activities_coll = self.db["activities"]
        self.goals_coll = self.db["goals"]
        self.conversations_coll = self.db["conversation_logs"]
    
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
                "last_interaction_time": "",
                "daily_interaction_count": 0,
                "last_interaction_date": "",
                "short_term_info": [],
                "general_info": {}  # Aseguramos que 'general_info' esté siempre presente
            }
            self.user_state_coll.insert_one(initial_state)
            return initial_state

        return {
            "user_id": doc["user_id"],
            "last_interaction_time": doc.get("last_interaction_time", ""),
            "daily_interaction_count": doc.get("daily_interaction_count", 0),
            "last_interaction_date": doc.get("last_interaction_date", ""),
            "short_term_info": doc.get("short_term_info", []),
            "general_info": doc.get("general_info", {})  # Aseguramos estructura correcta
        }

    
    def save_state(self, user_id: str, state: Dict[str, Any]) -> None:
        """
        Inserta o actualiza un user_state en 'user_states'.
        Se asegura de mantener la estructura base.
        """
        query = {"user_id": user_id}
        update_data = {
            "user_id": user_id,
            "last_interaction_time": state.get("last_interaction_time", ""),
            "daily_interaction_count": state.get("daily_interaction_count", 0),
            "last_interaction_date": state.get("last_interaction_date", ""),
            "short_term_info": state.get("short_term_info", []),
            "general_info": state.get("general_info", {})  # Garantizar existencia
        }

        self.user_state_coll.update_one(query, {"$set": update_data}, upsert=True)

    
    # Ejemplo para Activities
    def add_activity(self, user_id: str, activity_data: Dict[str, Any]):
        """
        Inserta una actividad en 'activities'.
        """
        activity_data["user_id"] = user_id
        activity_data["timestamp"] = datetime.utcnow().isoformat()
        # Podrías crear tu propio activity_id con ObjectId, o un str random
        activity_data["activity_id"] = str(ObjectId())
        self.activities_coll.insert_one(activity_data)
    
    # Podrías seguir con "get_activities(user_id)" o "save_goal()", etc.
