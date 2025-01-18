import discord
import asyncio
from config.settings import DISCORD_BOT_TOKEN

# Crear un cliente global de Discord con las intenciones adecuadas
intents = discord.Intents.default()  # Usa las intenciones predeterminadas
intents.messages = True  # Asegúrate de habilitar el manejo de mensajes
client = discord.Client(intents=intents)

# Callback opcional para manejar mensajes
global_message_callback = None

# Diccionario opcional para mapear user_id a canales
user_channels = {}

def register_message_callback(callback):
    """
    Registra la función que se ejecutará por cada mensaje recibido.
    La función callback debe tener la firma: async callback(message_text: str, author_id: str)
    """
    global global_message_callback
    global_message_callback = callback

@client.event
async def on_ready():
    print(f"[DISCORD] Bot conectado como {client.user}")

@client.event
async def on_message(message):
    # Evitamos responder a los propios mensajes del bot
    if message.author == client.user:
        return

    # Ejecutamos el callback registrado si existe
    if global_message_callback:
        await global_message_callback(message.content, str(message.author.id))

async def send_dm(user_id: str, text: str):
    """
    Envía un mensaje directo (DM) a un usuario dado su Discord user_id.
    """
    try:
        user = await client.fetch_user(int(user_id))
        await user.send(text)
        print(f"[DISCORD] Mensaje enviado a usuario {user_id}: {text}")
    except Exception as e:
        print(f"[DISCORD] Error enviando DM a {user_id}: {e}")

async def send_message_to_channel(channel_id: int, text: str):
    """
    Envía un mensaje a un canal específico, identificado por su ID.
    """
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
    """
    Inicia el bot utilizando el token configurado.
    """
    client.run(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    # Ejemplo de configuración y ejecución del bot
    async def example_callback(message_text, author_id):
        print(f"Mensaje recibido de {author_id}: {message_text}")

    register_message_callback(example_callback)
    run_bot()
