# /core/utils.py

from datetime import datetime, timedelta

def has_one_hour_passed(last_time_str: str) -> bool:
    """
    Verifica si ha pasado al menos una hora desde el tiempo dado.
    """
    if not last_time_str:
        return True  # Si no hay un tiempo registrado, asumimos que sí

    last_time = datetime.fromisoformat(last_time_str)
    return datetime.now() >= last_time + timedelta(hours=1)
