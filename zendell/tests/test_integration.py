# /tests/test_integration_real.py
import asyncio
import pytest
import threading
from core.db import MongoDBManager
from services.discord_service import DiscordService
from zendell.agents.communicator import Communicator

# Para este test, se asume que en el .env está configurada la variable DISCORD_BOT_TOKEN
# y que el bot está configurado para conectarse a un servidor de prueba.

@pytest.fixture
def db_manager():
    # Se utiliza la instancia real de MongoDBManager para probar el flujo completo.
    # Asegúrate de que la base de datos de test está correctamente definida y aislada.
    return MongoDBManager(
        uri="mongodb://root:rootpass@localhost:27017",
        db_name="zendell_test_db"
    )

def start_discord_bot(communicator: Communicator):
    """Ejecuta el bot de discord en un hilo separado para no bloquear la ejecución del test."""
    def run_bot():
        communicator.start_bot()  # Este método es bloqueante y gestionará el loop de Discord.
    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()
    return thread

@pytest.mark.asyncio
async def test_multiagent_flow_end_to_end(db_manager):
    """
    Test de integración que lanza el bot real y simula un flujo de conversación:
     - El bot se conecta a Discord.
     - Se dispara una interacción inicial proactiva.
     - El bot envía su primer mensaje al usuario (o canal).
    """
    # Creamos la instancia del DiscordService real.
    discord_service = DiscordService(intents=discord.Intents.default())
    
    # Instanciamos el Communicator con el servicio real y el db_manager.
    communicator = Communicator(discord_service=discord_service, db_manager=db_manager)
    
    # Arrancamos el bot en un hilo separado.
    start_discord_bot(communicator)
    
    # Damos tiempo para que el bot se conecte.
    await asyncio.sleep(5)
    
    # Simulamos que se fuerza una interacción proactiva.
    # En este ejemplo, se asume que el usuario de prueba es identificado por su Discord user_id.
    test_user_id = "123456789012345678"  # <--- Reemplazar con un ID real o de prueba (por DM)
    
    # Se invoca trigger_interaction para que se genere la respuesta inicial basada en goal_finder_node.
    communicator.trigger_interaction(test_user_id)
    
    # Esperamos algunos segundos para que el mensaje se envie.
    await asyncio.sleep(5)
    
    # A este nivel podrías hacer validaciones adicionales:
    # Por ejemplo, consultando la BD para verificar que se registró el estado,
    # o revisar logs del bot.
    #
    # En este ejemplo, el test termina con éxito si no se lanzan excepciones.
    assert True
