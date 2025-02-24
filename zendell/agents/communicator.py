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

    async def on_user_message(self, text: str, author_id: str):
        self.db_manager.save_conversation_message(
            user_id=author_id, role="user", content=text, extra_data={"step": "user_input"}
        )      
        buffer = self.conversations.get(author_id, [])
        buffer.append(text)
        self.conversations[author_id] = buffer

        if text.strip().upper() == "FIN":
            await self.handle_end_of_conversation(author_id)
            return

        if "mensaje anterior" in text.lower():
            await self.handle_previous_message(author_id)
            return

        flow = orchestrator_flow(author_id, text)
        final = flow["final_text"]
        await send_dm(author_id, final)

    async def handle_end_of_conversation(self, author_id: str):
        farewell = "¡Gracias! Te escribiré en la siguiente hora."
        self.db_manager.save_conversation_message(
            user_id=author_id, role="assistant", content=farewell
        )
        await send_dm(author_id, farewell)
        if author_id in self.conversations:
            self.conversations.pop(author_id)

    async def handle_previous_message(self, author_id: str):
        c = self.db_manager.conversations_coll.find(
            {"user_id": author_id}
        ).sort("timestamp", -1).limit(2)
        data = list(c)
        if len(data) < 2:
            await send_dm(author_id, "No existe un mensaje anterior.")
        else:
            msg = data[1]["content"]
            await send_dm(author_id, f"El mensaje anterior fue: '{msg}'")

    async def trigger_interaction(self, user_id: str):
        st = goal_finder_node(user_id)
        msgs = self.db_manager.conversations_coll.find(
            {"user_id": user_id, "role": "assistant"}
        ).sort("timestamp", -1).limit(1)
        arr = list(msgs)
        if arr:
            cont = arr[0].get("content","")
            if cont:
                await send_dm(user_id, cont)
