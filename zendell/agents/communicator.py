# /zendell/agents/communicator.py

import asyncio
from typing import Optional
from services.discord_service import DiscordService
from core.db import MongoDBManager
from agents.goal_finder import goal_finder_node  # Asegúrate de que esta ruta es correcta
from agents.activity_collector import activity_collector_node

class Communicator:
    """
    Agente encargado de coordinar la comunicación con el usuario
    a través de Discord.
    
    Para este flujo de pruebas:
      - Se espera que el bot mantenga un diálogo 1x1.
      - Cada mensaje del usuario se procesa mediante activity_collector_node.
      - Al finalizar la conversación (p. ej.: al recibir un comando "FIN"), se llama a goal_finder_node
        para generar la respuesta final y se envía un mensaje indicando la próxima interacción en 1 hora.
    """

    def __init__(self,
                 discord_service: DiscordService,
                 db_manager: MongoDBManager):
        self.discord_service = discord_service
        self.db_manager = db_manager

        # Registramos la función que manejará los mensajes entrantes
        self.discord_service.register_message_callback(self.on_user_message)

        # Para este ejemplo asumimos que el id del usuario de Discord es el mismo que usaremos para la BD.
        # Si se requiere otro mapeo se tendría que agregar la lógica correspondiente.
        
        # Opcionalmente, podrías definir un diccionario para acumular temporalmente la conversación.
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
        # (Por ejemplo, el usuario escribe "FIN" para indicar que terminó)
        if message_text.strip().upper() == "FIN":
            print(f"[Communicator] Se detectó finalización de conversación para user {author_id}.")
            
            # Procesamos la conversación: primero, almacenamos la actividad en la BD.
            # (Aquí podrías concatenar o procesar la conversación usando LLM para estructurarla antes de pasarlo)
            # Por simplicidad, se manda el último mensaje recibido.
            updated_state = activity_collector_node(
                state=self.db_manager.get_state(author_id),
                new_activity=" ".join(conversation)
            )
            self.db_manager.save_state(author_id, updated_state)
            print(f"[Communicator] Estado actualizado tras activity_collector: {updated_state}")
            
            # Se llama al goal_finder_node para generar la respuesta final.
            goal_state = goal_finder_node(author_id, self.db_manager)
            if "respuesta_inicial" in goal_state.get("general_info", {}):
                reply = goal_state["general_info"]["respuesta_inicial"]
            elif goal_state.get("short_term_info"):
                reply = goal_state["short_term_info"][-1]
            else:
                reply = "¡Hola! Algo salió mal en la generación de respuesta."
            
            # Se añade el mensaje de despedida indicando la próxima interacción en 1 hora.
            final_message = f"{reply}\n\n[El sistema conversará nuevamente en 1 hora.]"
            
            await self.send_message_to_user(author_id, final_message)
            
            # Limpiamos el acumulado de la conversación
            self.conversations.pop(author_id, None)
        else:
            # Si no es mensaje de finalización, podrías contestar algo de forma inmediata o simplemente esperar.
            # Por ejemplo, podrías notificar que se ha recibido el mensaje.
            await self.send_message_to_user(author_id, "Mensaje recibido, sigo escuchando...")

    async def send_message_to_user(self, user_id: str, text: str):
        """
        Envía un mensaje vía DM al usuario de Discord.
        """
        await self.discord_service.send_dm(user_id, text)

    def start_bot(self):
        """
        Inicia el bot de Discord (bloqueante).
        """
        self.discord_service.run_bot()

    def trigger_interaction(self, user_id: str):
        """
        Método auxiliar para forzar una interacción (por ejemplo, si se quiere iniciar proactivamente la conversación).
        """
        goal_state = goal_finder_node(user_id, self.db_manager)
        # Se decide qué mensaje usar de acuerdo al estado generado.
        if "respuesta_inicial" in goal_state.get("general_info", {}):
            message = goal_state["general_info"]["respuesta_inicial"]
        else:
            message = goal_state["short_term_info"][-1] if goal_state.get("short_term_info") else "¡Hola, algo salió raro!"
        
        # Enviamos el mensaje (aquí se asume que trigger_interaction se usa en un contexto asíncrono)
        asyncio.create_task(self.send_message_to_user(user_id, message))
