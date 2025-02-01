# zendell/services/discord_service.py

import discord
import asyncio
import os
from config.settings import DISCORD_BOT_TOKEN
from zendell.services.llm_provider import ask_gpt
from zendell.core.db import MongoDBManager  # <-- Necesitamos el db_manager para guardar el primer msg

close_app_task = None
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

client = discord.Client(intents=intents)
client.communicator = None
client.first_ready = False
client.default_channel = None

@client.event
async def on_ready():
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

    client.default_channel = found_channel
    print(f"[DEBUG] client.default_channel asignado: {client.default_channel}")

    if not client.first_ready:
        client.first_ready = True
        asyncio.create_task(send_first_message_system())

async def send_first_message_system():
    """
    Genera con GPT el primer mensaje de saludo y lo envía al canal por defecto.
    Lo guarda en la DB con un user_id genérico "system_init".
    """
    await asyncio.sleep(3.0)

    if not client.default_channel:
        print("[DISCORD] No hay un canal por defecto configurado (default_channel=None).")
        return

    # Prompt para GPT: generamos el primer saludo
    prompt = (
        "Eres Zendell, un sistema multiagente. Genera un mensaje de presentación amistoso en español. "
        "Saluda al usuario, explícale brevemente que eres un asistente y que te gustaría conocer su nombre, "
        "ocupación, gustos y metas. Indícale que estás para ayudarle. Sé amigable."
    )
    greeting = ask_gpt(prompt)
    if not greeting:
        greeting = "¡Hola! Soy Zendell, tu asistente multiagente. ¿Podrías presentarte?"

    try:
        # 1) Enviar mensaje al canal
        await client.default_channel.send(greeting)
        print(f"[DISCORD] Primer mensaje (sistema) enviado: {greeting}")

        # 2) Guardar en DB
        db_manager = MongoDBManager()
        db_manager.save_conversation_message(
            user_id="system_init",
            role="assistant",
            content=greeting,
            extra_data={"step": "first_message_system"}
        )
    except Exception as e:
        print(f"[DISCORD] Error enviando el primer mensaje: {e}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    raw_msg = message.content.strip() or message.clean_content.strip()
    print(f"[DISCORD] on_message => raw content: '{message.content}' | clean: '{message.clean_content}'")

    # Delegamos al communicator si existe
    if client.communicator and hasattr(client.communicator, "on_user_message"):
        await client.communicator.on_user_message(raw_msg, str(message.author.id))

async def send_dm(_user_id: str, text: str):
    channel = client.default_channel
    if not channel:
        print("[DISCORD] No hay un canal por defecto (default_channel=None).")
        return

    await asyncio.sleep(0.5)
    try:
        sent = await channel.send(text)
        print(f"[DISCORD] Mensaje enviado al canal {channel.id}: {text}")
        return sent
    except Exception as e:
        print(f"[DISCORD] Error enviando mensaje: {e}")

async def start_bot():
    await client.login(DISCORD_BOT_TOKEN)
    await asyncio.sleep(1)
    await client.connect()

async def schedule_app_close(timeout_minutes: int):
    print("[DISCORD] Timer de cierre iniciado")
    await asyncio.sleep(timeout_minutes * 60)
    print("[DISCORD] Cerrando aplicación por inactividad...")
    await client.close()
    os._exit(0)
