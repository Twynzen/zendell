# zendell/agents/communicator.py

import asyncio
from typing import Dict, Any
from zendell.core.db import MongoDBManager
from zendell.services.discord_service import send_dm
from zendell.agents.goal_finder import goal_finder_node
from zendell.agents.orchestrator import orchestrator_flow

class Communicator:
    def __init__(self, db_manager: MongoDBManager):
        self.db_manager = db_manager
        self.conversations = {}

    async def on_user_message(self, user_message: str, author_id: str):
        self.db_manager.save_conversation_message(
            user_id=author_id, role="user", content=user_message
        )
        buffer = self.conversations.get(author_id, [])
        buffer.append(user_message)
        self.conversations[author_id] = buffer

        if user_message.strip().upper() == "FIN":
            await self.handle_end_of_conversation(author_id)
            return

        if "mensaje anterior" in user_message.lower():
            await self.handle_previous_message(author_id)
            return

        user_state = self.db_manager.get_state(author_id)
        conversation_stage = user_state.get("conversation_stage", "initial")

        global_state_override = {}
        if conversation_stage in ["clarifier_last_hour", "clarifier_next_hour"]:
            global_state_override["clarifier_answer"] = user_message

        flow = orchestrator_flow(author_id, user_message, global_state_override)
        final_text = flow["final_text"]
        await send_dm(author_id, final_text)

    async def handle_end_of_conversation(self, author_id: str):
        farewell_text = "¡Gracias! Te escribiré en la siguiente hora."
        self.db_manager.save_conversation_message(
            user_id=author_id, role="assistant", content=farewell_text
        )
        await send_dm(author_id, farewell_text)
        if author_id in self.conversations:
            self.conversations.pop(author_id)

    async def handle_previous_message(self, author_id: str):
        cursor = self.db_manager.conversations_coll.find(
            {"user_id": author_id}
        ).sort("timestamp", -1).limit(2)
        data = list(cursor)
        if len(data) < 2:
            await send_dm(author_id, "No existe un mensaje anterior.")
        else:
            prev_message = data[1]["content"]
            await send_dm(author_id, f"El mensaje anterior fue: '{prev_message}'")

    async def trigger_interaction(self, user_id: str):
        state = goal_finder_node(user_id)
        cursor = self.db_manager.conversations_coll.find(
            {"user_id": user_id, "role": "assistant"}
        ).sort("timestamp", -1).limit(1)
        data = list(cursor)
        if data:
            last_content = data[0].get("content", "")
            if last_content:
                await send_dm(user_id, last_content)
