# tests/test_db.py

import pytest
from datetime import datetime
from core.db import DBManager, init_db

# Si quieres aislar tu DB de test, crea otra URL:
TEST_DATABASE_URL = "postgresql://user:password@localhost:5432/test_database"

@pytest.fixture(scope="module")
def db_manager():
    # Iniciamos la base de datos (crear tablas si no existen)
    init_db()  
    # Instanciamos DBManager apuntando a la BD de test
    db = DBManager(connection_string=TEST_DATABASE_URL)
    return db

def test_save_and_get_state(db_manager):
    # 1) Guardamos un state
    user_id = "test_user_100"
    test_state = {
        "lastInteractionTime": datetime.utcnow().isoformat(),
        "dailyInteractionCount": 2,
        "lastInteractionDate": "2025-01-15",
        "shortTermInfo": ["Probar SQLAlchemy", "Configurar environment"],
        "generalInfo": {"debug": True}
    }
    db_manager.save_state(user_id, test_state)

    # 2) Leemos el state
    saved = db_manager.get_state(user_id)
    assert saved != {}, "Se esperaba un state no vacío"
    assert saved["dailyInteractionCount"] == 2
    assert saved["shortTermInfo"] == ["Probar SQLAlchemy", "Configurar environment"]
    assert saved["generalInfo"] == {"debug": True}
