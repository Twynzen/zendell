# zendell/services/discord_service.py

import discord
import asyncio
import os
from config.settings import DISCORD_BOT_TOKEN

print("discord_service module:", __name__)

close_app_task = None
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True  # Asegura que tenemos la intención de leer guilds
intents.message_content = True

client = discord.Client(intents=intents)
client.communicator = None
client.first_ready = False
client.default_channel = None  # Almacenaremos aquí el canal "enviable"

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
            else:
                print(f"  -> Canal: {channel.name} (ID: {channel.id}) - SIN PERMISO")

    print(f"[DEBUG] found_channel al final del bucle: {found_channel}")
    client.default_channel = found_channel
    print(f"[DEBUG] client.default_channel asignado: {client.default_channel}")

    if not client.first_ready:
        client.first_ready = True
        if client.communicator:
            print("[DISCORD] on_ready: Se programará la interacción del Communicator...")
            asyncio.create_task(delayed_trigger_interaction())

async def delayed_trigger_interaction():
    await asyncio.sleep(5.0)
    if client.communicator:
        print("[DISCORD] delayed_trigger_interaction: Llamando a trigger_interaction...")
        await client.communicator.trigger_interaction("")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    global close_app_task
    if close_app_task and not close_app_task.done():
        close_app_task.cancel()
        print("[DISCORD] El usuario respondió a tiempo. Timer de cierre cancelado.")

    if client.communicator and hasattr(client.communicator, "on_user_message"):
        await client.communicator.on_user_message(message.content, str(message.author.id))

async def send_dm(_user_id: str, text: str):
    print(f"[DISCORD] Intentando enviar mensaje: {text}")
    print(f"[DEBUG] Valor actual de client.default_channel: {client.default_channel}")

    channel = client.default_channel
    if not channel:
        print("[DISCORD] No hay un canal por defecto configurado (default_channel=None).")
        return

    await asyncio.sleep(1.0)  # Extra margen
    try:
        result = await channel.send(text)
        print(f"[DISCORD] Mensaje enviado al canal {channel.id}: {text}")
        return result
    except Exception as e:
        print(f"[DISCORD] Ocurrió un error enviando el mensaje: {e}")

async def start_bot():
    await client.login(DISCORD_BOT_TOKEN)
    await asyncio.sleep(1)
    await client.connect()

async def schedule_app_close(timeout_minutes: int):
    print("[DISCORD] Timer de cierre iniciado")
    await asyncio.sleep(timeout_minutes * 60)
    print("[DISCORD] No hubo respuesta del usuario en el tiempo límite. Cerrando aplicación...")
    await client.close()
    os._exit(0)
