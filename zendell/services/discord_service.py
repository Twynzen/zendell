# /services/discord_service.py

import discord
import asyncio
from config.settings import DISCORD_BOT_TOKEN

class DiscordService(discord.Client):
    """
    Servicio que implementa el bot de Discord.
    
    - Registra una callback para mensajes.
    - Permite enviar mensajes vía DM a usuarios o a canales específicos.
    """
    def __init__(self, **options):
        super().__init__(**options)
        self.message_callback = None
        # Opcional: Un diccionario para mapear user_id a algún canal si lo necesitas
        self.user_channels = {}

    def register_message_callback(self, callback):
        """
        Registra la función que se ejecutará por cada mensaje recibido.
        La función callback debe tener la firma: async callback(message_text: str, author_id: str)
        """
        self.message_callback = callback

    async def on_ready(self):
        print(f"[DISCORD] Bot conectado como {self.user}")

    async def on_message(self, message):
        # Evitamos responder a los propios mensajes del bot
        if message.author == self.user:
            return

        # Aquí podrías filtrar mensajes en canales o DMs si lo requieres.
        if self.message_callback:
            await self.message_callback(message.content, str(message.author.id))

    async def send_dm(self, user_id: str, text: str):
        """
        Envía un mensaje direct (DM) a un usuario dado su Discord user_id.
        """
        try:
            user = await self.fetch_user(int(user_id))
            await user.send(text)
            print(f"[DISCORD] Mensaje enviado a usuario {user_id}: {text}")
        except Exception as e:
            print(f"[DISCORD] Error enviando DM a {user_id}: {e}")

    async def send_message_to_channel(self, channel_id: int, text: str):
        """
        Envía un mensaje a un canal específico, identificado por su ID.
        """
        try:
            channel = self.get_channel(channel_id)
            if channel:
                await channel.send(text)
                print(f"[DISCORD] Mensaje enviado al canal {channel_id}: {text}")
            else:
                print(f"[DISCORD] No se encontró el canal con ID {channel_id}")
        except Exception as e:
            print(f"[DISCORD] Error enviando mensaje al canal {channel_id}: {e}")

    def run_bot(self):
        """
        Inicia el bot utilizando el token configurado.
        """
        super().run(DISCORD_BOT_TOKEN)
