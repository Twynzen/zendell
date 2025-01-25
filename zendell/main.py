# main.py
import asyncio
import warnings

from datetime import datetime
from zendell.core.db import MongoDBManager
from zendell.agents.communicator import Communicator
from zendell.services.discord_service import client, start_bot

warnings.filterwarnings("ignore", category=DeprecationWarning)


async def hourly_interaction_loop(communicator, user_ids):
    """
    Ejemplo de rutina que cada cierto tiempo (1 hora) 
    llama a 'communicator.trigger_interaction(user_id)'
    para ejecutar la lógica de goal_finder, etc.
    """
    while True:
        for user_id in user_ids:
            await communicator.trigger_interaction(user_id)
        # Esperamos 1 hora
        await asyncio.sleep(3600)


async def main_async():
    """
    Arranque principal de la aplicación.
    1. Instancia MongoDBManager y Communicator.
    2. Inicia el bot de Discord.
    3. (Opcional) Lanza una tarea en segundo plano 
       para interacciones cada hora.
    """
    db_manager = MongoDBManager(
        uri="mongodb://root:rootpass@localhost:27017/?authSource=admin",
        db_name="zendell_db"
    )

    # Creamos el Communicator y se lo inyectamos al Discord client.
    communicator = Communicator(db_manager)
    client.communicator = communicator

    print("[MAIN] Iniciando bot de Discord con login/connect...")

    # Esta lista de user_ids podría venir de la base de datos,
    # o un config. Por simplicidad, agregamos un ejemplo estático.
    user_ids_to_check = ["1234567890"]  # Reemplaza con IDs reales de tu proyecto.

    # Iniciamos dos tareas en paralelo:
    # 1) la conexión del bot a Discord
    # 2) el loop que cada hora llama a communicator.trigger_interaction
    loop = asyncio.get_event_loop()
    task_bot = loop.create_task(start_bot())
    task_hourly = loop.create_task(hourly_interaction_loop(communicator, user_ids_to_check))

    # Esperamos a que las dos tareas terminen (aunque la del bot 
    # se ejecuta hasta desconexión)
    await asyncio.gather(task_bot, task_hourly)


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
