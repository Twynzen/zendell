# core/db.py

from datetime import datetime
from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from bson.objectid import ObjectId

MONGO_URL = "mongodb://root:rootpass@localhost:27017/?authSource=admin"

class MongoDBManager:
    def __init__(self, uri: str = MONGO_URL, db_name: str = "zendell_db"):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]

        self.users_coll = self.db["users"]
        self.user_state_coll = self.db["user_states"]
        self.activities_coll = self.db["activities"]
        self.goals_coll = self.db["goals"]
        self.conversations_coll = self.db["conversation_logs"]

    def get_state(self, user_id: str) -> Dict[str, Any]:
        doc = self.user_state_coll.find_one({"user_id": user_id})
        if not doc:
            initial_state = {
                "user_id": user_id,
                "last_interaction_time": "",
                "daily_interaction_count": 0,
                "last_interaction_date": "",
                "short_term_info": [],
                "general_info": {},
                "customer_name": "",   # <-- AÑADIDO para guardar nombre de usuario
                "mood_overall": "",
                "last_summary": ""
            }
            self.user_state_coll.insert_one(initial_state)
            return initial_state
        
        # Nos aseguramos de devolver un dict que contenga 'customer_name'
        doc.setdefault("customer_name", "")
        doc.setdefault("mood_overall", "")
        doc.setdefault("last_summary", "")
        return doc

    def save_state(self, user_id: str, state: Dict[str, Any]) -> None:
        query = {"user_id": user_id}
        update_data = {
            "user_id": user_id,
            "last_interaction_time": state.get("last_interaction_time", ""),
            "daily_interaction_count": state.get("daily_interaction_count", 0),
            "last_interaction_date": state.get("last_interaction_date", ""),
            "short_term_info": state.get("short_term_info", []),
            "general_info": state.get("general_info", {}),
            "mood_overall": state.get("mood_overall", ""),
            "last_summary": state.get("last_summary", ""),
            "customer_name": state.get("customer_name", "")
        }
        self.user_state_coll.update_one(query, {"$set": update_data}, upsert=True)

    def log_message(
        self,
        user_id: str,
        message: str,
        is_bot: bool,
        speaker_name: str,
        agent_name: str = "communicator",
        conversation_id: Optional[str] = None
    ):
        log_data = {
            "user_id": user_id,
            "timestamp": datetime.utcnow(),
            "message": message,
            "is_bot": is_bot,
            "speaker_name": speaker_name,
            "agent_name": agent_name,
        }
        if conversation_id:
            log_data["conversation_id"] = conversation_id
        
        self.conversations_coll.insert_one(log_data)

    def get_conversation_history(
        self,
        user_id: str,
        limit: int = 20,
        conversation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = {"user_id": user_id}
        if conversation_id:
            query["conversation_id"] = conversation_id
        
        cursor = (
            self.conversations_coll.find(query)
            .sort("timestamp", 1)
            .limit(limit)
        )
        return list(cursor)
