from agents.communicator import Communicator
from core.db import MongoDBManager
from services.discord_service import run_bot
import pytest
import asyncio
import threading
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)



# Para este test, se asume que en el .env está configurada la variable DISCORD_BOT_TOKEN
# y que el bot está configurado para conectarse a un servidor de prueba.

@pytest.fixture
def db_manager():
    return MongoDBManager(
        uri="mongodb://root:rootpass@localhost:27017",
        db_name="zendell_test_db"
    )
    

def start_discord_bot():
    def run():
        run_bot()
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread

@pytest.mark.asyncio
async def test_multiagent_flow_end_to_end(db_manager):
    communicator = Communicator(db_manager=db_manager)
    start_discord_bot()

    # Simula interacción
    user_id = "123456789012345678"
    communicator.trigger_interaction(user_id)

    await asyncio.sleep(5)  # Da tiempo para la interacción
    assert True