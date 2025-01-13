# core/db.py

from datetime import datetime
from typing import Optional, Dict, Any, List
# SQLAlchemy imports
from sqlalchemy import (
    Column, String, Integer, DateTime, Text, JSON, ForeignKey, create_engine
)
from sqlalchemy.orm import (
    declarative_base, relationship, sessionmaker
)

# -----------------------------------------------------------------------------
#                              MODELOS
# -----------------------------------------------------------------------------
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    userId = Column(String, primary_key=True, index=True)
    phoneNumber = Column(String, nullable=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)

    # Relación 1:1 con UserState
    state = relationship("UserState", back_populates="user", uselist=False)

    # Relación 1:N con Activity
    activities = relationship("Activity", back_populates="user")

    # Relación 1:N con Goal
    goals = relationship("Goal", back_populates="user")


class UserState(Base):
    __tablename__ = "user_states"

    userId = Column(String, ForeignKey("users.userId"), primary_key=True)
    lastInteractionTime = Column(DateTime, nullable=True)
    dailyInteractionCount = Column(Integer, default=0)
    lastInteractionDate = Column(String, nullable=True)
    shortTermInfo = Column(JSON, default=[])
    generalInfo = Column(JSON, default={})

    user = relationship("User", back_populates="state")


class Activity(Base):
    __tablename__ = "activities"

    activityId = Column(String, primary_key=True, index=True)
    userId = Column(String, ForeignKey("users.userId"))
    activity = Column(String, nullable=False)
    type = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="activities")


class ConversationLog(Base):
    __tablename__ = "conversation_logs"

    conversationId = Column(String, primary_key=True, index=True)
    userId = Column(String, ForeignKey("users.userId"))
    message = Column(Text, nullable=False)
    sender = Column(String, nullable=False)  # "user" o "system"
    createdAt = Column(DateTime, default=datetime.utcnow)


class Goal(Base):
    __tablename__ = "goals"

    goalId = Column(String, primary_key=True, index=True)
    userId = Column(String, ForeignKey("users.userId"))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="pending")  # "pending", "inProgress", "achieved"
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="goals")


# -----------------------------------------------------------------------------
#                           ENGINE Y SESSION
# -----------------------------------------------------------------------------
# Aquí defines tu URL de la BD (ajusta usuario, pass, host y nombre de DB)
DATABASE_URL = "postgresql://user:password@localhost:5432/mydatabase"

# Creamos el engine en modo sincrono
engine = create_engine(DATABASE_URL, echo=True)

# Creamos una factoría de sesiones
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    """
    Crea las tablas si no existen. En producción, usar migraciones (Alembic).
    """
    Base.metadata.create_all(bind=engine)


# -----------------------------------------------------------------------------
#                            DB MANAGER
# -----------------------------------------------------------------------------
class DBManager:
    """
    Clase que maneja la lectura/escritura de datos.
    Por ahora, solo ejemplos get_state() y save_state() para UserState.
    Extender con más métodos para Activity, Goals, etc.
    """

    def __init__(self, connection_string: str = DATABASE_URL):
        self._engine = create_engine(connection_string, echo=False)
        self._Session = sessionmaker(bind=self._engine, autoflush=False, autocommit=False)
        # Puedes crear las tablas aquí si gustas
        Base.metadata.create_all(bind=self._engine)

    def get_session(self):
        """
        Retorna una sesión de SQLAlchemy (context manager).
        """
        return self._Session()

    def get_state(self, user_id: str) -> Dict[str, Any]:
        """
        Busca en user_states. Retorna un dict con la info del userState.
        Si no existe, retorna {}
        """
        with self.get_session() as session:
            us_state = session.query(UserState).filter_by(userId=user_id).first()
            if not us_state:
                return {}

            return {
                "userId": us_state.userId,
                "lastInteractionTime": (
                    us_state.lastInteractionTime.isoformat() if us_state.lastInteractionTime else ""
                ),
                "dailyInteractionCount": us_state.dailyInteractionCount,
                "lastInteractionDate": us_state.lastInteractionDate,
                "shortTermInfo": us_state.shortTermInfo,
                "generalInfo": us_state.generalInfo
            }

    def save_state(self, user_id: str, state: Dict[str, Any]) -> None:
        """
        Inserta o actualiza un UserState según userId.
        Crea un User si no existe.
        """
        with self.get_session() as session:
            # Revisamos si ya existe
            us_state = session.query(UserState).filter_by(userId=user_id).first()

            if not us_state:
                # Crear uno nuevo
                us_state = UserState(userId=user_id)
                session.add(us_state)

                # Aseguramos que existe un User
                user = session.query(User).filter_by(userId=user_id).first()
                if not user:
                    user = User(
                        userId=user_id,
                        name="Placeholder",  # O data real si lo tuvieras
                        createdAt=datetime.utcnow()
                    )
                    session.add(user)

            # Actualizamos campos del UserState
            if state.get("lastInteractionTime"):
                # Convertir de str ISO8601 a datetime
                us_state.lastInteractionTime = datetime.fromisoformat(state["lastInteractionTime"])
            else:
                us_state.lastInteractionTime = None

            us_state.dailyInteractionCount = state.get("dailyInteractionCount", 0)
            us_state.lastInteractionDate = state.get("lastInteractionDate", "")
            us_state.shortTermInfo = state.get("shortTermInfo", [])
            us_state.generalInfo = state.get("generalInfo", {})

            session.commit()
