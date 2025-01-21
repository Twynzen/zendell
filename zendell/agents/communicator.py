# agents/communicator.py
import asyncio
from datetime import datetime
from services.discord_service import register_message_callback, send_dm, run_bot
from core.db import MongoDBManager
from agents.goal_finder import goal_finder_node
from agents.activity_collector import activity_collector_node

class Communicator:
    """
    Agente encargado de coordinar la comunicación con el usuario a través de Discord.
    """

    def __init__(self, db_manager: MongoDBManager):
        self.db_manager = db_manager
        # Registramos la función que manejará los mensajes entrantes
        register_message_callback(self.on_user_message)
        self.conversations = {}  # {discord_user_id: [mensaje1, mensaje2, ...]}

    async def on_user_message(self, message_text: str, author_id: str):
        print(f"[Communicator] Mensaje recibido de user_id={author_id}: {message_text}")
        conversation_log = {
        "user_id": author_id,
        "timestamp": datetime.utcnow().isoformat(),
        "message": message_text,
        "is_bot": False  # O True si fuera la respuesta del bot
        }
        self.db_manager.conversations_coll.insert_one(conversation_log)

        conversation = self.conversations.get(author_id, [])
        conversation.append(message_text)
        self.conversations[author_id] = conversation

        if message_text.strip().upper() == "FIN":
            print(f"[Communicator] Finalización de conversación para user {author_id}.")
            try:
                current_state = self.db_manager.get_state(author_id)
            except Exception as e:
                print(f"[Communicator] Error leyendo la BD: {e}. Usando estado temporal.")
                current_state = {}
            updated_state = activity_collector_node(
                state=current_state,
                new_activity=" ".join(conversation)
            )
            try:
                self.db_manager.save_state(author_id, updated_state)
            except Exception as e:
                print(f"[Communicator] Error guardando estado en BD: {e}")

            goal_state = goal_finder_node(author_id, self.db_manager)
            if "respuesta_inicial" in goal_state.get("general_info", {}):
                reply = goal_state["general_info"]["respuesta_inicial"]
            elif goal_state.get("short_term_info"):
                reply = goal_state["short_term_info"][-1]
            else:
                reply = "¡Hola! Algo salió mal generando la respuesta."

            final_message = f"{reply}\n\n[El sistema conversará nuevamente en 1 hora.]"
            await send_dm(author_id, final_message)
            self.conversations.pop(author_id, None)
        else:
            await send_dm(author_id, "Mensaje recibido, sigo escuchando...")

    def start_bot(self):
        run_bot()

    async def trigger_interaction(self, _user_id: str):
        print("[Communicator] Iniciando interacción (sin depender de user_id).")
        goal_state = goal_finder_node("", self.db_manager)
        if not goal_state.get("general_info"):
            message = "¡Hola! La base de datos no responde, pero te saludo en modo temporal."
        elif "respuesta_inicial" in goal_state.get("general_info", {}):
            message = goal_state["general_info"]["respuesta_inicial"]
        else:
            message = goal_state["short_term_info"][-1] if goal_state.get("short_term_info") else "¡Hola, algo salió raro!"
        await send_dm("", message)

