# zendell/core/db_models.py

from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field, asdict

def current_datetime() -> str:
    """Devuelve la fecha y hora actual en formato ISO."""
    return datetime.utcnow().isoformat()

@dataclass
class BaseModel:
    """Clase base para todos los modelos de datos."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el objeto a un diccionario."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Crea una instancia desde un diccionario."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

@dataclass
class EntityReference(BaseModel):
    """Referencia a una entidad."""
    entity_id: str
    entity_type: str  # person, place, organization, concept, etc.
    relationship: str  # familia, amigo, trabajo, etc.
    context: str = ""  # contexto en el que se mencionó

@dataclass
class ActivityMention(BaseModel):
    """Mención de una actividad."""
    activity_id: str
    context: str = ""

@dataclass
class Memory(BaseModel):
    """Unidad de memoria del sistema."""
    content: str
    source: str  # conversation, activity, analysis, etc.
    importance: int = 1  # 1-10, donde 10 es lo más importante
    recency: float = 1.0  # 0-1, donde 1 es lo más reciente
    reference_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=current_datetime)
    last_accessed: str = field(default_factory=current_datetime)
    access_count: int = 0

@dataclass
class PersonEntity(BaseModel):
    """Entidad de tipo persona."""
    entity_id: str
    name: str
    relationship: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    first_mentioned: str = field(default_factory=current_datetime)
    last_mentioned: str = field(default_factory=current_datetime)
    mention_count: int = 1
    importance: int = 5  # 1-10

@dataclass
class PlaceEntity(BaseModel):
    """Entidad de tipo lugar."""
    entity_id: str
    name: str
    type: str = ""  # home, work, restaurant, etc.
    attributes: Dict[str, Any] = field(default_factory=dict)
    first_mentioned: str = field(default_factory=current_datetime)
    last_mentioned: str = field(default_factory=current_datetime)
    mention_count: int = 1
    importance: int = 5  # 1-10

@dataclass
class ConceptEntity(BaseModel):
    """Entidad de tipo concepto."""
    entity_id: str
    name: str
    category: str = ""  # interest, concern, aspiration, etc.
    attributes: Dict[str, Any] = field(default_factory=dict)
    first_mentioned: str = field(default_factory=current_datetime)
    last_mentioned: str = field(default_factory=current_datetime)
    mention_count: int = 1
    importance: int = 5  # 1-10

@dataclass
class ClarificationQA(BaseModel):
    """Pregunta y respuesta de clarificación."""
    question: str
    answer: str = ""
    timestamp: str = field(default_factory=current_datetime)
    reasoning: str = ""

@dataclass
class Activity(BaseModel):
    """Actividad del usuario."""
    activity_id: str
    user_id: str
    title: str
    category: str
    time_context: str  # past, future
    timestamp: str = field(default_factory=current_datetime)
    original_message: str = ""
    clarification_questions: List[str] = field(default_factory=list)
    clarifier_responses: List[Dict[str, Any]] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    analysis: str = ""
    completed: bool = False
    importance: int = 5  # 1-10

@dataclass
class ConversationMessage(BaseModel):
    """Mensaje en una conversación."""
    user_id: str
    role: str  # user, assistant, system
    content: str
    timestamp: str = field(default_factory=current_datetime)
    conversation_stage: str = "unknown"
    entities_mentioned: List[EntityReference] = field(default_factory=list)
    activities_mentioned: List[ActivityMention] = field(default_factory=list)
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GeneralInfo(BaseModel):
    """Información general sobre el usuario."""
    name: str = ""
    ocupacion: str = ""
    gustos: str = ""
    metas: str = ""
    cumpleanos: str = ""
    ubicacion: str = ""
    relaciones: List[Dict[str, str]] = field(default_factory=list)
    intereses: List[str] = field(default_factory=list)
    valores: List[str] = field(default_factory=list)
    custom_attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UserState(BaseModel):
    """Estado del usuario en la conversación."""
    user_id: str
    name: str = "Desconocido"
    last_interaction_time: str = ""
    daily_interaction_count: int = 0
    last_interaction_date: str = ""
    conversation_stage: str = "initial"
    recent_topics: List[str] = field(default_factory=list)
    mood: str = "neutral"
    energy_level: str = "normal"
    attention_level: str = "normal"
    current_context: str = ""
    short_term_info: List[str] = field(default_factory=list)
    conversation_stage_override: Optional[str] = None
    general_info: Dict[str, Any] = field(default_factory=dict)
    interaction_history: List[Dict[str, Any]] = field(default_factory=list)
    activities_last_hour: List[Dict[str, Any]] = field(default_factory=list)
    activities_next_hour: List[Dict[str, Any]] = field(default_factory=list)
    clarifier_history: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class UserProfile(BaseModel):
    """Perfil completo del usuario."""
    user_id: str
    created_at: str = field(default_factory=current_datetime)
    last_updated: str = field(default_factory=current_datetime)
    general_info: GeneralInfo = field(default_factory=GeneralInfo)
    long_term_summary: str = ""  # Resumen generado por el sistema
    personality_traits: Dict[str, float] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    important_dates: Dict[str, str] = field(default_factory=dict)
    routines: List[Dict[str, Any]] = field(default_factory=list)
    life_areas: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    known_entities: Dict[str, List[str]] = field(default_factory=dict)  # {entity_type: [entity_ids]}

@dataclass
class SystemMemory(BaseModel):
    """Memoria del sistema."""
    memory_id: str
    content: str
    type: str  # observation, insight, learning, strategy
    relevance: int = 5  # 1-10
    created_at: str = field(default_factory=current_datetime)
    last_accessed: str = field(default_factory=current_datetime)
    access_count: int = 0
    related_entities: List[Dict[str, Any]] = field(default_factory=list)
    related_activities: List[Dict[str, Any]] = field(default_factory=list)