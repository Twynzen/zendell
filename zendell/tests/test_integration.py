# /tests/test_integration.py
import asyncio
import pytest
from unittest.mock import AsyncMock
from services.discord_service import DiscordService
from zendell.agents.communicator import Communicator
from core.db import MongoDBManager

class FakeDiscordService(DiscordService):
    """Fake Discord Service para testear sin conectar a Discord."""
    async def send_dm(self, user_id: str, text: str):
        print(f"[FAKE DISCORD] Enviando DM a {user_id}: {text}")
    
    def run_bot(self):
        print("[FAKE DISCORD] run_bot llamado")

@pytest.fixture
def db_manager():
    # Instancia real o mock de MongoDBManager para pruebas
    db = MongoDBManager(uri="mongodb://root:rootpass@localhost:27017", db_name="zendell_test_db")
    return db

@pytest.mark.asyncio
async def test_complete_flow(db_manager):
    fake_service = FakeDiscordService()
    communicator = Communicator(discord_service=fake_service, db_manager=db_manager)
    
    # Simulamos el envío de varios mensajes y la terminación con "FIN"
    user_id = "123456789"  # ID de Discord de prueba
    # Simulamos mensajes entrantes:
    await communicator.on_user_message("Hola, ¿cómo estás?", user_id)
    await communicator.on_user_message("Quiero contar algo importante.", user_id)
    await communicator.on_user_message("FIN", user_id)
    
    # Aquí se debería verificar (por ejemplo, en la BD o en la salida impresa) que se realizó
    # la secuencia: acumulación de mensajes, llamado a activity_collector y goal_finder, etc.
    # Puedes incluir asserts específicos según lo que esperas.
