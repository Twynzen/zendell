import asyncio
from typing import Optional
from services.discord_service import (
    client, register_message_callback, send_dm, run_bot
)
from core.db import MongoDBManager
from agents.goal_finder import goal_finder_node  # Asegúrate de que esta ruta es correcta
from agents.activity_collector import activity_collector_node

class Communicator:
    """
    Agente encargado de coordinar la comunicación con el usuario
    a través de Discord.
    """

    def __init__(self, db_manager: MongoDBManager):
        self.db_manager = db_manager

        # Registramos la función que manejará los mensajes entrantes
        register_message_callback(self.on_user_message)

        # Diccionario para acumular temporalmente la conversación
        self.conversations = {}  # {discord_user_id: [mensaje1, mensaje2, ...]}

    async def on_user_message(self, message_text: str, author_id: str):
        """
        Maneja el mensaje recibido desde Discord.
        """
        print(f"[Communicator] Mensaje recibido de user_id={author_id}: {message_text}")

        # Acumula los mensajes en la conversación
        conversation = self.conversations.get(author_id, [])
        conversation.append(message_text)
        self.conversations[author_id] = conversation

        # Validamos si el mensaje indica finalización de la conversación.
        if message_text.strip().upper() == "FIN":
            print(f"[Communicator] Se detectó finalización de conversación para user {author_id}.")
            
            # Procesamos la conversación y almacenamos la actividad en la BD.
            updated_state = activity_collector_node(
                state=self.db_manager.get_state(author_id),
                new_activity=" ".join(conversation)
            )
            self.db_manager.save_state(author_id, updated_state)
            print(f"[Communicator] Estado actualizado tras activity_collector: {updated_state}")
            
            # Generamos la respuesta final usando goal_finder_node.
            goal_state = goal_finder_node(author_id, self.db_manager)
            if "respuesta_inicial" in goal_state.get("general_info", {}):
                reply = goal_state["general_info"]["respuesta_inicial"]
            elif goal_state.get("short_term_info"):
                reply = goal_state["short_term_info"][-1]
            else:
                reply = "¡Hola! Algo salió mal en la generación de respuesta."
            
            final_message = f"{reply}\n\n[El sistema conversará nuevamente en 1 hora.]"
            
            await send_dm(author_id, final_message)

            # Limpiamos el acumulado de la conversación
            self.conversations.pop(author_id, None)
        else:
            # Si no es un mensaje de finalización, respondemos algo simple.
            await send_dm(author_id, "Mensaje recibido, sigo escuchando...")

    def start_bot(self):
        """
        Inicia el bot de Discord (bloqueante).
        """
        run_bot()

    def trigger_interaction(self, user_id: str):
        """
        Método auxiliar para forzar una interacción (por ejemplo, si se quiere iniciar proactivamente la conversación).
        """
        goal_state = goal_finder_node(user_id, self.db_manager)
        if "respuesta_inicial" in goal_state.get("general_info", {}):
            message = goal_state["general_info"]["respuesta_inicial"]
        else:
            message = goal_state["short_term_info"][-1] if goal_state.get("short_term_info") else "¡Hola, algo salió raro!"
        
        # Enviamos el mensaje (en un contexto asíncrono)
        asyncio.create_task(send_dm(user_id, message))
