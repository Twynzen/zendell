# zendell/agents/communicator.py

import asyncio
from core.utils import get_timestamp
from zendell.agents.goal_finder import goal_finder_node
from zendell.agents.orchestrator import orchestrator_flow
from zendell.services.discord_service import send_dm

class Communicator:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.conversations = {}

    async def on_user_message(self, text: str, author_id: str):
        self.db_manager.save_conversation_message(
        user_id=author_id,
        role="user",
        content=text,
        extra_data={"step": "user_input"}
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
        # Se pasa el db manager a orchestrator_flow a través del global_state.
        flow = orchestrator_flow(author_id, text, self.db_manager)
        final = flow["final_text"]
        await send_dm(author_id, final)

    async def handle_end_of_conversation(self, author_id: str):
        farewell = "¡Gracias! Te escribiré en la siguiente hora."
        self.db_manager.save_conversation_message(user_id=author_id, role="assistant", content=farewell)
        await send_dm(author_id, farewell)
        if author_id in self.conversations:
            self.conversations.pop(author_id)

    async def handle_previous_message(self, author_id: str):
        c = self.db_manager.conversations_coll.find({"user_id": author_id}).sort("timestamp", -1).limit(2)
        data = list(c)
        if len(data) < 2:
            await send_dm(author_id, "No existe un mensaje anterior.")
        else:
            msg = data[1]["content"]
            await send_dm(author_id, f"El mensaje anterior fue: '{msg}'")

    async def trigger_interaction(self, user_id: str):
        """
        Inicia una interacción con el usuario basada en el contexto actual.
        """
        # Obtener estado antes y después de goal_finder para detectar cambios
        state_before = self.db_manager.get_state(user_id)
        result = goal_finder_node(user_id, self.db_manager)
        state_after = self.db_manager.get_state(user_id)
        
        # Verificar si goal_finder indica que no debemos interactuar
        if not state_after.get("can_interact", True):
            print(f"{get_timestamp()}","[COMMUNICATOR] No es momento de interactuar según goal_finder.")
            return
        
        # Buscar mensajes recientes del asistente
        msgs = self.db_manager.conversations_coll.find(
            {"user_id": user_id, "role": "assistant"},
            sort=[("timestamp", -1)],
            limit=1
        )
        arr = list(msgs)
        
        # Solo enviar si hay un mensaje disponible y se actualizó el estado
        if arr and (str(state_before) != str(state_after)):
            cont = arr[0].get("content", "")
            if cont:
                await send_dm(user_id, cont)