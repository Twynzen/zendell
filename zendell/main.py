import asyncio
import warnings
from zendell.core.db import MongoDBManager
from zendell.agents.communicator import Communicator
from zendell.services.discord_service import client, start_bot

warnings.filterwarnings("ignore", category=DeprecationWarning)

async def hourly_interaction_loop(communicator):
    while True:
        user_ids = communicator.db_manager.user_state_coll.distinct("user_id")
        for user_id in user_ids:
            if user_id:
                print(f"[HOURLY INTERACTION] Iniciando interacción con user_id: {user_id}")
                await communicator.trigger_interaction(user_id)
        await asyncio.sleep(3600)

async def main_async():
    db_manager = MongoDBManager(uri="mongodb://root:rootpass@localhost:27017/?authSource=admin", db_name="zendell_db")
    communicator = Communicator(db_manager)
    client.communicator = communicator
    print("[MAIN] Iniciando bot de Discord con login/connect...")
    loop = asyncio.get_event_loop()
    task_bot = loop.create_task(start_bot())
    task_hourly = loop.create_task(hourly_interaction_loop(communicator))
    await asyncio.gather(task_bot, task_hourly)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()