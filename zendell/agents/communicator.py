import asyncio
from datetime import datetime
from typing import Dict, Any

from zendell.core.db import MongoDBManager
from zendell.services.discord_service import send_dm
from zendell.agents.goal_finder import goal_finder_node
# OJO: Importamos el orquestador
from zendell.agents.orchestrator import orchestrator_flow

class Communicator:
    """
    Agente encargado de coordinar la comunicación con el usuario a través de Discord.
    Maneja la llegada de mensajes de usuario, los guarda en DB y decide la respuesta.
    """

    def __init__(self, db_manager: MongoDBManager):
        self.db_manager = db_manager
        # Diccionario en RAM para la conversación activa
        # { user_id: [mensajes recibidos temporalmente], ... }
        self.conversations = {}

    async def on_user_message(self, message_text: str, author_id: str):
        """
        Evento principal llamado cuando el usuario (author_id) envía un mensaje en Discord.
        """
        print(f"[Communicator] Mensaje recibido de user_id={author_id}: {message_text}")

        # 1. Guardar el mensaje en la DB como rol="user"
        self.db_manager.save_conversation_message(
            user_id=author_id,
            role="user",
            content=message_text,
            extra_data={"step": "communicator_on_user_message"}
        )

        # 2. Mantener en RAM un buffer de conversación
        conversation = self.conversations.get(author_id, [])
        conversation.append(message_text)
        self.conversations[author_id] = conversation

        # 3. Control de "FIN" u otra palabra clave
        if message_text.strip().upper() == "FIN":
            await self.handle_end_of_conversation(author_id, conversation)
        else:
            # Ahora, en lugar de llamar activity_collector_node directamente,
            # usamos el orquestador para que realice todo el pipeline
            result = orchestrator_flow(author_id, message_text)
            final_text = result["final_text"]

            # Enviamos ese texto final al usuario
            await send_dm(author_id, final_text)

    async def handle_end_of_conversation(self, author_id: str, conversation: list):
        """
        Cuando el usuario escribe 'FIN', consideramos que desea cerrar la conversación actual.
        """
        print(f"[Communicator] Finalizando conversación para user {author_id}.")

        # Llamamos a la DB para obtener el estado
        try:
            current_state = self.db_manager.get_state(author_id)
        except Exception as e:
            print(f"[Communicator] Error leyendo la BD: {e}. Usando estado temporal.")
            current_state = {}

        # Podemos pasar toda la conversación como una "actividad" final (opcional)
        joined_conversation = " ".join(conversation)
        # Si deseas, podrías llamar de nuevo al orquestador aquí con joined_conversation
        # o simplemente al activity_collector_node... depende de tu gusto.
        # global_state = {
        #     "user_id": author_id,
        #     "last_message": joined_conversation,
        #     "activities": current_state.get("activities", []),
        #     "analysis": {},
        #     "recommendation": []
        # }
        # updated_state = activity_collector_node(global_state)

        # Generar respuesta final usando goal_finder o un "chao"
        farewell = "¡Gracias por la charla! Volveré a escribirte en la próxima hora."
        self.db_manager.save_conversation_message(
            user_id=author_id,
            role="assistant",
            content=farewell,
            extra_data={"step": "handle_end_of_conversation"}
        )
        await send_dm(author_id, farewell)

        # Limpiar el buffer en RAM
        self.conversations.pop(author_id, None)

    async def trigger_interaction(self, user_id: str):
        """
        Llamado cada X tiempo (por ejemplo, 1 hora).
        goal_finder_node revisa si debe iniciar una nueva conversación con el user.
        """
        print("[Communicator] Disparando interacción cíclica con goal_finder...")
        # goal_finder_node se encarga de generar un msg y guardarlo en DB con role=assistant
        # si procede (si ha pasado una hora, etc.)
        final_state = goal_finder_node(user_id)
        # De paso, enviamos el mensaje al user (si se generó).
        if final_state.get("last_interaction_time"):
            last_msg_cursor = self.db_manager.conversations_coll.find(
                {"user_id": user_id, "role": "assistant"}
            ).sort("timestamp", -1).limit(1)
            last_msg = list(last_msg_cursor)
            if last_msg:
                content = last_msg[0].get("content", "")
                if content:
                    await send_dm(user_id, content)
