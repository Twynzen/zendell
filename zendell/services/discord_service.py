# services/discord_service.py
import discord
import asyncio
from config.settings import DISCORD_BOT_TOKEN  # Solo se requiere el token
import asyncio
import os

close_app_task = None  # Para poder cancelarlo desde otras partes

intents = discord.Intents.default()
intents.messages = True
client = discord.Client(intents=intents)

global_message_callback = None

def register_message_callback(callback):
    global global_message_callback
    global_message_callback = callback

@client.event
async def on_ready():
    print(f"[DISCORD] Bot conectado como {client.user}")
    # Listar guilds y canales donde se pueda enviar mensajes.
    for guild in client.guilds:
        print(f"[DISCORD] Guild detectado: {guild.name} (ID: {guild.id})")
        for channel in guild.text_channels:
            perms = channel.permissions_for(guild.me)
            if perms.send_messages:
                print(f"  -> Canal: {channel.name} (ID: {channel.id}) - Enviable")
            else:
                print(f"  -> Canal: {channel.name} (ID: {channel.id}) - SIN PERMISO")

async def send_dm(_user_id: str, text: str):
    """
    Envía un mensaje sin depender del user_id.
    Siempre se busca el primer canal de texto en el que el bot tenga permiso.
    Se asegura de ejecutar el envío de mensaje en el event loop del cliente Discord,
    ya que éste se corre en un thread diferente al del test.
    """
    try:
        print(f"[DISCORD] Intentando enviar mensaje: {text}")
        channel = None
        for guild in client.guilds:
            for c in guild.text_channels:
                perms = c.permissions_for(guild.me)
                if perms.send_messages:
                    channel = c
                    break
            if channel:
                break
        if channel:
            # Programamos el envío en el loop del cliente usando run_coroutine_threadsafe
            future = asyncio.run_coroutine_threadsafe(channel.send(text), client.loop)
            # await wrapping the future to wait in our async context:
            result = await asyncio.wrap_future(future)
            print(f"[DISCORD] Mensaje enviado al canal {channel.id}: {text}")
            return result
        else:
            print("[DISCORD] No se encontró un canal activo para enviar el mensaje.")
    except Exception as e:
        print(f"[DISCORD] Error enviando mensaje: {e}")

async def send_message_to_channel(channel_id: int, text: str):
    try:
        channel = client.get_channel(channel_id)
        if channel:
            await channel.send(text)
            print(f"[DISCORD] Mensaje enviado al canal {channel_id}: {text}")
        else:
            print(f"[DISCORD] No se encontró el canal con ID {channel_id}")
    except Exception as e:
        print(f"[DISCORD] Error enviando mensaje al canal {channel_id}: {e}")

def run_bot():
    client.run(DISCORD_BOT_TOKEN)
    


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    # Si el usuario responde, cancelamos si el timer está corriendo
    if close_app_task and not close_app_task.done():
        close_app_task.cancel()
        print("[DISCORD] El usuario respondió a tiempo. Timer de cierre cancelado.")

    if global_message_callback:
        await global_message_callback(message.content, str(message.author.id))
    

async def schedule_app_close(timeout_minutes: int):
    print("[DISCORD] Timer de cierre iniciado")
    await asyncio.sleep(timeout_minutes * 60)  # 10 min => 600s
    print("[DISCORD] No hubo respuesta del usuario en el tiempo límite. Cerrando aplicación...")
    # Cierra la conexión con Discord y finaliza la app
    await client.close()
    os._exit(0)  # Forzamos la salida


if __name__ == "__main__":
    async def example_callback(message_text, author_id):
        print(f"Mensaje recibido de {author_id}: {message_text}")
    register_message_callback(example_callback)
    run_bot()
