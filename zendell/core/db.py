# zendell/core/db.py

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
                "name": "Desconocido",
                "last_interaction_time": "",
                "daily_interaction_count": 0,
                "last_interaction_date": "",
                "short_term_info": [],
                "general_info": {"metas": "", "gustos": "", "ocupacion": ""},
                "conversation_stage": "initial",
                "interaction_history": []
            }
            self.user_state_coll.insert_one(initial_state)
            return initial_state
        return {
            "user_id": doc["user_id"],
            "name": doc.get("name", "Desconocido"),
            "last_interaction_time": doc.get("last_interaction_time", ""),
            "daily_interaction_count": doc.get("daily_interaction_count", 0),
            "last_interaction_date": doc.get("last_interaction_date", ""),
            "short_term_info": doc.get("short_term_info", []),
            "general_info": doc.get("general_info", {}),
            "conversation_stage": doc.get("conversation_stage", "initial"),
            "interaction_history": doc.get("interaction_history", [])
        }

    def save_state(self, user_id: str, state: Dict[str, Any]) -> None:
        query = {"user_id": user_id}
        update_data = {
            "user_id": user_id,
            "name": state.get("name", "Desconocido"),
            "last_interaction_time": state.get("last_interaction_time", ""),
            "daily_interaction_count": state.get("daily_interaction_count", 0),
            "last_interaction_date": state.get("last_interaction_date", ""),
            "short_term_info": state.get("short_term_info", []),
            "general_info": state.get("general_info", {}),
            "conversation_stage": state.get("conversation_stage", "initial"),
            "interaction_history": state.get("interaction_history", [])
        }
        self.user_state_coll.update_one(query, {"$set": update_data}, upsert=True)

    def add_activity(self, user_id: str, activity_data: Dict[str, Any]):
        activity_data["user_id"] = user_id
        activity_data["timestamp"] = datetime.utcnow().isoformat()
        activity_data["activity_id"] = str(ObjectId())
        self.activities_coll.insert_one(activity_data)

    def save_conversation_message(self, user_id: str, role: str, content: str,
                                  extra_data: Optional[Dict[str, Any]] = None) -> None:
        timestamp_str = datetime.utcnow().isoformat()
        message_doc = {"user_id": user_id, "role": role, "content": content, "timestamp": timestamp_str}
        if extra_data:
            message_doc.update(extra_data)
        self.conversations_coll.insert_one(message_doc)

    def get_user_conversation(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        cursor = self.conversations_coll.find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
        return list(cursor)[::-1]