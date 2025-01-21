# main.py
import asyncio
import warnings
from zendell.core.db import MongoDBManager
from zendell.agents.communicator import Communicator
from zendell.services.discord_service import client, start_bot

warnings.filterwarnings("ignore", category=DeprecationWarning)

async def main_async():
    db_manager = MongoDBManager(
        uri="mongodb://root:rootpass@localhost:27017/?authSource=admin",
        db_name="zendell_db"
    )
    communicator = Communicator(db_manager)
    client.communicator = communicator

    print("[MAIN] Iniciando bot de Discord con login/connect...")
    await start_bot()  # Bloquea hasta que se cierre la conexión

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
