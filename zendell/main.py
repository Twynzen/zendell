import asyncio
import warnings
import signal
import sys
from datetime import datetime
from core.utils import get_timestamp
from zendell.core.db import MongoDBManager
from zendell.core.memory_manager import MemoryManager
from zendell.agents.communicator import Communicator
from zendell.agents.goal_finder import goal_finder_node
from zendell.services.discord_service import client, start_bot

# Suprimir advertencias de depreciación
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Variable global para controlar el bucle principal
running = True

async def hourly_interaction_loop(communicator, interval_minutes=5):  # Cambiado de 60 a 5 minutos
    """
    Bucle principal que inicia interacciones periódicas con los usuarios.
    """
    # Convertir minutos a segundos
    interval_seconds = interval_minutes * 60
    
    # Calcular horas (para pasar a goal_finder_node)
    hours_between = interval_minutes / 60
    
    print(f"{get_timestamp()}",f"[MAIN] Iniciando bucle de interacción cada {interval_minutes} minutos")
    
    while running:
        try:
            # Obtener todos los IDs de usuario distintos
            user_ids = communicator.db_manager.user_states_coll.distinct("user_id")
            
            # Iniciar interacción con cada usuario activo
            for user_id in user_ids:
                if user_id:
                    print(f"{get_timestamp()}",f"[HOURLY INTERACTION] Iniciando interacción con user_id: {user_id}")
                    
                    # Verificar último tiempo de interacción antes de iniciar
                    state = communicator.db_manager.get_state(user_id)
                    last_time = state.get("last_interaction_time", "")
                    
                    # Calcular tiempo transcurrido
                    if last_time:
                        try:
                            last_datetime = datetime.fromisoformat(last_time)
                            elapsed_minutes = (datetime.now() - last_datetime).total_seconds() / 60
                            
                            # Solo interactuar si ha pasado suficiente tiempo
                            if elapsed_minutes < interval_minutes:
                                print(f"{get_timestamp()}",f"[HOURLY INTERACTION] Omitiendo interacción con {user_id}, "
                                     f"solo han pasado {elapsed_minutes:.1f} minutos de {interval_minutes}")
                                continue
                        except ValueError:
                            # Si hay un error en el formato de tiempo, continuar con la interacción
                            pass
                    
                    # MODIFICADO: Pasar el nuevo intervalo como horas a goal_finder_node
                    goal_finder_node(user_id, communicator.db_manager, hours_between)
                    await communicator.trigger_interaction(user_id)
            
            # Esperar hasta la próxima iteración
            await asyncio.sleep(interval_seconds)
            
        except Exception as e:
            print(f"{get_timestamp()}",f"[ERROR] en bucle de interacción: {e}")
            # Continuar con la siguiente iteración tras un breve retraso
            await asyncio.sleep(60)
            
async def maintenance_tasks_loop(db_manager, interval_hours=24):
    """
    Bucle para tareas de mantenimiento y optimización de la base de datos.
    
    Args:
        db_manager: Instancia del gestor de base de datos
        interval_hours: Intervalo entre mantenimientos en horas (por defecto 24)
    """
    # Convertir horas a segundos
    interval_seconds = interval_hours * 3600
    
    print(f"{get_timestamp()}",f"{get_timestamp()}",f"[MAIN] Iniciando bucle de mantenimiento cada {interval_hours} horas")
    
    while running:
        try:
            print(f"{get_timestamp()}","[MAINTENANCE] Iniciando tareas de mantenimiento")
            
            # Inicializar el gestor de memoria
            memory_manager = MemoryManager(db_manager)
            
            # Obtener todos los usuarios
            user_ids = db_manager.user_states_coll.distinct("user_id")
            
            for user_id in user_ids:
                if not user_id:
                    continue
                
                print(f"{get_timestamp()}",f"[MAINTENANCE] Procesando usuario: {user_id}")
                
                # Generar reflexión a largo plazo (actualiza perfil del usuario)
                try:
                    memory_manager.generate_long_term_reflection(user_id)
                    print(f"{get_timestamp()}",f"[MAINTENANCE] Reflexión a largo plazo generada para {user_id}")
                except Exception as e:
                    print(f"{get_timestamp()}",f"[ERROR] al generar reflexión para {user_id}: {e}")
                
                # Generar insights del sistema
                try:
                    insights = db_manager.generate_system_insights(user_id)
                    print(f"{get_timestamp()}",f"[MAINTENANCE] {len(insights)} insights generados para {user_id}")
                except Exception as e:
                    print(f"{get_timestamp()}",f"[ERROR] al generar insights para {user_id}: {e}")
            
            # Esperar hasta la próxima iteración
            await asyncio.sleep(interval_seconds)
            
        except Exception as e:
            print(f"{get_timestamp()}",f"[ERROR] en bucle de mantenimiento: {e}")
            # Continuar con la siguiente iteración tras un breve retraso
            await asyncio.sleep(3600)

def handle_exit(sig, frame):
    """Manejador de señales para salida limpia."""
    global running
    print(f"{get_timestamp()}",f"[MAIN] Recibida señal de interrupción ({sig}). Cerrando...")
    running = False
    
    # Cerrar la conexión de Discord
    if client:
        asyncio.create_task(client.close())
    
    # Esperar un momento para que las tareas en curso terminen
    loop = asyncio.get_event_loop()
    loop.call_later(2, lambda: sys.exit(0))

async def main_async():
    """Función principal asíncrona."""
    # Registrar manejadores de señales para salida limpia
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    print(f"{get_timestamp()}","[MAIN] Iniciando ZENDELL - Sistema Multiagente Proactivo")
    
    try:
        # Inicializar conexión a la base de datos
        db_manager = MongoDBManager(
            uri="mongodb://root:rootpass@localhost:27017/?authSource=admin", 
            db_name="zendell_db"
        )
        print(f"{get_timestamp()}","[MAIN] Conexión a MongoDB establecida")
        
        # Inicializar el comunicador
        communicator = Communicator(db_manager)
        client.communicator = communicator
        print(f"{get_timestamp()}","[MAIN] Comunicador inicializado")
        
        # Obtener el bucle de eventos
        loop = asyncio.get_event_loop()
        
        # Crear tareas para los bucles principales
        task_bot = loop.create_task(start_bot())
        task_hourly = loop.create_task(hourly_interaction_loop(communicator))
        task_maintenance = loop.create_task(maintenance_tasks_loop(db_manager))
        
        # Esperar a que todas las tareas terminen
        await asyncio.gather(task_bot, task_hourly, task_maintenance)
        
    except Exception as e:
        print(f"{get_timestamp()}",f"[ERROR CRÍTICO] en main_async: {e}")
        sys.exit(1)

def main():
    """Punto de entrada principal."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print(f"{get_timestamp()}","[MAIN] Programa terminado por interrupción de teclado")
    except Exception as e:
        print(f"{get_timestamp()}",f"[ERROR FATAL] en main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()