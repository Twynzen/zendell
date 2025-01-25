# zendell/services/discord_service.py

import discord
import asyncio
import os
from config.settings import DISCORD_BOT_TOKEN

"""
Este módulo maneja la conexión con Discord. 
Define el cliente, on_ready, on_message, etc.
Lo fundamental para tu caso es:
 - En 'on_ready' buscamos un canal "enviable" y lo guardamos como 'client.default_channel'.
 - Luego, con 'delayed_trigger_interaction()', esperamos unos segundos y 
   llamamos 'communicator.trigger_interaction' para que el bot envíe el primer mensaje.
"""

close_app_task = None
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
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

    # Asignamos el primer canal encontrable donde el bot tiene permisos
    client.default_channel = found_channel
    print(f"[DEBUG] client.default_channel asignado: {client.default_channel}")

    if not client.first_ready:
        client.first_ready = True
        if client.communicator:
            print("[DISCORD] on_ready: Se programará la interacción inicial del Communicator...")
            asyncio.create_task(delayed_trigger_interaction())


async def delayed_trigger_interaction():
    """
    Esperamos unos segundos a que todo esté listo, 
    y luego llamamos a 'trigger_interaction' para que el bot 
    envíe su primer mensaje.
    """
    await asyncio.sleep(5.0)
    if client.communicator:
        print("[DISCORD] delayed_trigger_interaction: Llamando a trigger_interaction...")
        # Aquí puedes usar un user_id real o dejarlo en blanco si tu Communicator 
        # maneja un 'broadcast' a varios usuarios, etc.
        await client.communicator.trigger_interaction("1234567890")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Si content está vacío, intentamos usar clean_content
    raw_msg = message.content.strip()
    if not raw_msg:
        raw_msg = message.clean_content.strip()

    print(f"[DISCORD] on_message => raw content: '{message.content}' | clean: '{message.clean_content}'")

    if client.communicator and hasattr(client.communicator, "on_user_message"):
        await client.communicator.on_user_message(
            raw_msg,
            str(message.author.id)
        )


async def send_dm(_user_id: str, text: str):
    """
    Enviamos mensajes al canal por defecto. 
    Si quisieras enviar un DM directo, tendrías que 
    buscar el user y hacer user.send(...) 
    """
    channel = client.default_channel
    if not channel:
        print("[DISCORD] No hay un canal por defecto configurado (default_channel=None).")
        return

    await asyncio.sleep(1.0)  # Pequeño margen
    try:
        result = await channel.send(text)
        print(f"[DISCORD] Mensaje enviado al canal {channel.id}: {text}")
        return result
    except Exception as e:
        print(f"[DISCORD] Error enviando el mensaje: {e}")


async def start_bot():
    """
    Inicia el bot y bloquea hasta desconexión.
    """
    await client.login(DISCORD_BOT_TOKEN)
    await asyncio.sleep(1)
    await client.connect()


async def schedule_app_close(timeout_minutes: int):
    """
    Ejemplo de tarea para cerrar la app si no hay interacción 
    en un cierto tiempo. (Opcional)
    """
    print("[DISCORD] Timer de cierre iniciado")
    await asyncio.sleep(timeout_minutes * 60)
    print("[DISCORD] No hubo respuesta del usuario en el tiempo límite. Cerrando aplicación...")
    await client.close()
    os._exit(0)
