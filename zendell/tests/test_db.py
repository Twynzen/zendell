import pytest
from datetime import datetime, timezone
from core.db import MongoDBManager
from core.utils import get_timestamp

@pytest.fixture(scope="module")
def db_manager():
    """
    Crea una instancia de MongoDBManager apuntando a una DB de test,
    y al final limpia esa DB.
    """
    print(f"{get_timestamp()}","[SETUP] Creando instancia de MongoDBManager...")
    db = MongoDBManager(
        uri="mongodb://root:rootpass@localhost:27017/?authSource=admin", 
        db_name="zendell_test_db"
    )
    yield db
#    print(f"{get_timestamp()}","[TEARDOWN] Limpiando base de datos de prueba...")
#    db.client.drop_database("zendell_test_db")


def test_save_and_get_state(db_manager):
    """
    Testea que podamos guardar un user_state y luego leerlo.
    """
    user_id = "test_user_100"
    test_state = {
        "lastInteractionTime": datetime.now(timezone.utc).isoformat(),
        "dailyInteractionCount": 2,
        "lastInteractionDate": "2025-01-15",
        "shortTermInfo": ["Probar MongoDB", "Configurar environment"],
        "generalInfo": {"debug": True}
    }

    print(f"{get_timestamp()}","\n[STEP 1] Guardando el state en la base de datos...")
    db_manager.save_state(user_id, test_state)

    print(f"{get_timestamp()}","[STEP 2] Recuperando el state desde la base de datos...")
    saved = db_manager.get_state(user_id)

    print(f"{get_timestamp()}",f"[DEBUG] State recuperado: {saved}")

    assert saved != {}, "Se esperaba un state no vacío"
    assert saved["dailyInteractionCount"] == 2
    assert saved["shortTermInfo"] == ["Probar MongoDB", "Configurar environment"]
    assert saved["generalInfo"] == {"debug": True}

    print(f"{get_timestamp()}",f"\n[SUCCESS] Test finalizado correctamente para user_id={user_id}")
