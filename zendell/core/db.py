# core/db.py

class DBManager:
    def __init__(self, connection_string: str):
        # Configura la conexión real (SQLAlchemy, PyMongo, etc.)
        pass

    def get_state(self, user_id: str) -> dict:
        # SELECT or read from DB => return dict
        pass

    def save_state(self, user_id: str, state: dict) -> None:
        # INSERT or UPDATE => commit
        pass
