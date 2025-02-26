# zendell/core/memory_manager.py
# Clase MemoryManager para centralizar operaciones de memoria (recuperación y actualización)

from typing import List, Dict, Any

class MemoryManager:
    def __init__(self, db):
        self.db = db

    def get_recent_context(self, user_id: str, limit: int = 8) -> List[Dict[str, Any]]:
        return self.db.get_user_conversation(user_id, limit)

    def update_state(self, user_id: str, updates: Dict[str, Any]) -> None:
        state = self.db.get_state(user_id)
        state.update(updates)
        self.db.save_state(user_id, state)
