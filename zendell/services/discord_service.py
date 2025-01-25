# zendell/services/discord_service.py

import discord
import asyncio
import os
from config.settings import DISCORD_BOT_TOKEN
from zendell.services.llm_provider import ask_gpt

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
        # Envía el primer mensaje (usando GPT) sin asociarlo a un user_id
        asyncio.create_task(send_first_message_system())

async def send_first_message_system():
    """
    Genera con GPT el primer mensaje de saludo y lo envía al canal por defecto,
    sin vincularlo a un user_id, para evitar crear user_states con un ID ficticio.
    """
    await asyncio.sleep(3.0)  # breve espera para asegurar que todo esté listo

    if not client.default_channel:
        print("[DISCORD] No hay un canal por defecto configurado (default_channel=None).")
        return

    # Llamamos a GPT para generar un saludo inicial
    prompt = (
        "Eres Zendell, un sistema multiagente. Genera un mensaje de presentación amistoso "
        "para saludar a quien lea este canal, invitando a que se presenten con su nombre, gustos y metas."
    )
    greeting = ask_gpt(prompt)
    if not greeting:
        greeting = "¡Hola! Soy Zendell, listo para asistirte."

    # Enviamos al canal por defecto
    try:
        msg_sent = await client.default_channel.send(greeting)
        print(f"[DISCORD] Primer mensaje (sistema) enviado: {greeting}")
    except Exception as e:
        print(f"[DISCORD] Error enviando el primer mensaje: {e}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Evitamos vacíos si es un reply con mención, etc.
    raw_msg = message.content.strip() or message.clean_content.strip()

    print(f"[DISCORD] on_message => raw content: '{message.content}' | clean: '{message.clean_content}'")

    # Delegamos al communicator si existe
    if client.communicator and hasattr(client.communicator, "on_user_message"):
        await client.communicator.on_user_message(
            raw_msg,
            str(message.author.id)
        )

async def send_dm(_user_id: str, text: str):
    """
    Envía un mensaje al canal por defecto por simplicidad.
    (Podrías enviar DM directo si obtienes discord.User)
    """
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
    """
    Inicia el bot y bloquea hasta desconexión.
    """
    await client.login(DISCORD_BOT_TOKEN)
    await asyncio.sleep(1)
    await client.connect()

async def schedule_app_close(timeout_minutes: int):
    print("[DISCORD] Timer de cierre iniciado")
    await asyncio.sleep(timeout_minutes * 60)
    print("[DISCORD] Cerrando aplicación por inactividad...")
    await client.close()
    os._exit(0)
