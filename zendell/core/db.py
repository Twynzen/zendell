# core/db.py

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from bson.objectid import ObjectId

# Nota: Si vas a usar Docker con la URI:
MONGO_URL = "mongodb://root:rootpass@localhost:27017"  # Ajusta usuario y pass según tu docker-compose

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
        Retorna un dict con la info del userState, o {} si no existe.
        """
        doc = self.user_state_coll.find_one({"userId": user_id})
        if not doc:
            return {}
        
        # Convertimos campos a lo que necesitemos
        return {
            "userId": doc["userId"],
            "lastInteractionTime": doc.get("lastInteractionTime", ""),
            "dailyInteractionCount": doc.get("dailyInteractionCount", 0),
            "lastInteractionDate": doc.get("lastInteractionDate", ""),
            "shortTermInfo": doc.get("shortTermInfo", []),
            "generalInfo": doc.get("generalInfo", {})
        }
    
    def save_state(self, user_id: str, state: Dict[str, Any]) -> None:
        """
        Inserta o actualiza un user_state en 'user_states'.
        También se asegura de que exista un 'users' con userId = user_id.
        """
        # 1) Asegurar user
        user_doc = self.users_coll.find_one({"userId": user_id})
        if not user_doc:
            # Creamos un user placeholder
            new_user = {
                "userId": user_id,
                "name": "Placeholder",
                "createdAt": datetime.now(timezone.utc).isoformat()
            }
            self.users_coll.insert_one(new_user)

        # 2) Insert/update userState
        query = {"userId": user_id}
        update_data = {
            "userId": user_id,
            "lastInteractionTime": state.get("lastInteractionTime", ""),
            "dailyInteractionCount": state.get("dailyInteractionCount", 0),
            "lastInteractionDate": state.get("lastInteractionDate", ""),
            "shortTermInfo": state.get("shortTermInfo", []),
            "generalInfo": state.get("generalInfo", {})
        }
        
        # upsert: True => si no existe, lo crea
        self.user_state_coll.update_one(query, {"$set": update_data}, upsert=True)
    
    # Ejemplo para Activities
    def add_activity(self, user_id: str, activity_data: Dict[str, Any]):
        """
        Inserta una actividad en 'activities'.
        """
        activity_data["userId"] = user_id
        activity_data["timestamp"] = datetime.utcnow().isoformat()
        # Podrías crear tu propio activityId con ObjectId, o un str random
        activity_data["activityId"] = str(ObjectId())
        self.activities_coll.insert_one(activity_data)
    
    # Podrías seguir con "get_activities(user_id)" o "save_goal()", etc.
