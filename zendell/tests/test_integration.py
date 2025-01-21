# tests/test_integration.py
import pytest
import asyncio
import threading
import warnings
from zendell.agents.communicator import Communicator
from zendell.core.db import MongoDBManager
from zendell.services.discord_service import run_bot

warnings.filterwarnings("ignore", category=DeprecationWarning)

@pytest.fixture
def db_manager():
    return MongoDBManager(
        uri="mongodb://root:rootpass@localhost:27017/?authSource=admin",
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

    #await asyncio.sleep(1)  # Espera a que el bot se conecte y liste los canales

    # Llamada a trigger_interaction como coroutine
    await communicator.trigger_interaction("")

    #await asyncio.sleep(1)  # Da tiempo para la interacción
    assert True
