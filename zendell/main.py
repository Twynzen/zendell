import asyncio
import warnings
from datetime import datetime
from zendell.core.db import MongoDBManager
from zendell.agents.communicator import Communicator
from zendell.services.discord_service import client, start_bot

warnings.filterwarnings("ignore", category=DeprecationWarning)


async def hourly_interaction_loop(communicator):
    """
    Rutina que cada cierto tiempo (1 hora) llama a 'communicator.trigger_interaction(user_id)'
    para ejecutar la lógica de goal_finder con todos los usuarios reales.
    """
    while True:
        # Leer los user_ids desde la base de datos
        user_ids = communicator.db_manager.user_state_coll.distinct("user_id")
        for user_id in user_ids:
            if user_id:  # Asegurarnos de no procesar IDs vacíos
                print(f"[HOURLY INTERACTION] Iniciando interacción con user_id: {user_id}")
                await communicator.trigger_interaction(user_id)
        # Esperar 1 hora antes del próximo ciclo
        await asyncio.sleep(3600)


async def main_async():
    """
    Arranque principal de la aplicación:
    1. Instancia MongoDBManager y Communicator.
    2. Inicia el bot de Discord.
    3. Lanza una tarea en segundo plano para las interacciones cíclicas por hora.
    """
    db_manager = MongoDBManager(
        uri="mongodb://root:rootpass@localhost:27017/?authSource=admin",
        db_name="zendell_db"
    )

    # Creamos el Communicator y se lo inyectamos al cliente de Discord
    communicator = Communicator(db_manager)
    client.communicator = communicator

    print("[MAIN] Iniciando bot de Discord con login/connect...")

    # Iniciamos las tareas paralelas:
    # 1. La conexión del bot a Discord
    # 2. El loop que cada hora llama a communicator.trigger_interaction
    loop = asyncio.get_event_loop()
    task_bot = loop.create_task(start_bot())
    task_hourly = loop.create_task(hourly_interaction_loop(communicator))

    # Esperamos a que ambas tareas terminen
    await asyncio.gather(task_bot, task_hourly)


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
