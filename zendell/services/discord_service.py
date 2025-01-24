# zendell/services/discord_service.py

import discord
import asyncio
import os

from zendell.services.llm_provider import ask_gpt
from zendell.core.db import MongoDBManager
from config.settings import DISCORD_BOT_TOKEN

"""
Este módulo maneja la conexión con Discord. 
Aquí definimos el client, los eventos de on_ready y on_message, etc.
La lógica principal de conversación está en 'Communicator', 
pero 'on_message' redirecciona a Communicator.on_user_message().
"""

close_app_task = None

# Ajustamos intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True

client = discord.Client(intents=intents)
client.communicator = None  # Se inyecta desde fuera (ej: main.py)
client.first_ready = False
client.default_channel = None

@client.event
async def on_ready():
    """
    Se llama cuando el bot se conecta a Discord.
    Intentamos encontrar un canal para enviar mensajes por defecto.
    """
    print(f"[DISCORD] Bot conectado como {client.user}")

    found_channel = None
    for guild in client.guilds:
        print(f"[DISCORD] Guild detectado: {guild.name} (ID: {guild.id})")
        for channel in guild.text_channels:
            perms = channel.permissions_for(guild.me)
            if perms.send_messages:
                print(f"  -> Canal: {channel.name} (ID: {channel.id}) - Enviable")
                if not found_channel:
                    found_channel = channel
            else:
                print(f"  -> Canal: {channel.name} (ID: {channel.id}) - SIN PERMISO")

    client.default_channel = found_channel
    print(f"[DEBUG] Canal por defecto asignado: {client.default_channel}")

    if not client.first_ready:
        client.first_ready = True
        # Aquí podemos disparar una interacción inicial si queremos
        print("[DISCORD] Bot listo para recibir mensajes.")

@client.event
async def on_message(message):
    """
    Captura todos los mensajes en canales donde el bot tiene permiso.
    Evitamos auto-responder si el bot mismo es el autor.
    """
    if message.author == client.user:
        return

    global close_app_task
    if close_app_task and not close_app_task.done():
        close_app_task.cancel()
        print("[DISCORD] Timer de cierre cancelado (usuario respondió).")

    # Si tenemos una instancia de 'Communicator', 
    # delegamos la lógica de respuesta
    if client.communicator and hasattr(client.communicator, "on_user_message"):
        await client.communicator.on_user_message(
            message.content,
            str(message.author.id)  # user_id
        )

async def send_dm(user_id: str, text: str):
    """
    Enviar un mensaje al 'canal por defecto' o, en un futuro,
    un DM directo al user. Por ahora, iremos con default_channel.
    """
    if not client.default_channel:
        print("[DISCORD] No hay default_channel definido. Abortando envío de mensaje.")
        return

    await asyncio.sleep(0.5)  # Pequeña pausa
    try:
        await client.default_channel.send(text)
        print(f"[DISCORD] Mensaje enviado a canal {client.default_channel.id}: {text}")
    except Exception as e:
        print(f"[DISCORD] Error enviando mensaje a Discord: {e}")

async def start_bot():
    """
    Inicia el login y la conexión del bot. Bloquea hasta desconexión.
    """
    await client.login(DISCORD_BOT_TOKEN)
    await asyncio.sleep(1)
    await client.connect()

async def schedule_app_close(timeout_minutes: int):
    """
    Ejemplo de tarea para cerrar la app si no hay interacción 
    en un cierto tiempo. (Opcional en tu proyecto)
    """
    print("[DISCORD] Timer de cierre iniciado")
    await asyncio.sleep(timeout_minutes * 60)
    print("[DISCORD] Cerrando aplicación por inactividad...")
    await client.close()
    os._exit(0)
