# zendell/core/graph.py
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List, Dict, Any

# Importamos los agentes (nodos) desde la carpeta agents
from zendell.agents.activity_collector import activity_collector_node
from zendell.agents.analyzer import analyzer_node
from zendell.agents.recommender import recommender_node

# 1) Definimos el schema del estado global que se compartirá entre los nodos.
#    Puedes ampliar este schema si tu flujo lo requiere.
class GlobalState(TypedDict):
    user_id: str                         # Identificador único del usuario.
    customer_name: str                   # Nombre del usuario.
    activities: List[Dict[str, str]]     # Lista de actividades con su tipo.
    analysis: Dict[str, Any]             # Resultado del análisis (ej. "tono", "intención", etc.).
    recommendation: List[str]            # Recomendaciones generadas por el recommender.
    last_message: str                    # Texto del último mensaje que se manejó.
    conversation_context: List[Dict[str, Any]]  # Historial parcial (si lo deseas en RAM).
    # ... añade más campos si fuera necesario.

# 2) Creamos el grafo usando StateGraph y le pasamos el schema GlobalState
builder = StateGraph(GlobalState)

# 3) Añadimos los nodos (agentes) al grafo
builder.add_node("activity_collector", activity_collector_node)
builder.add_node("analyzer", analyzer_node)
builder.add_node("recommender", recommender_node)

# 4) Definimos las conexiones entre los nodos
#    El flujo empieza recogiendo actividades, luego analiza, luego recomienda.
builder.add_edge(START, "activity_collector")
builder.add_edge("activity_collector", "analyzer")
builder.add_edge("analyzer", "recommender")
builder.add_edge("recommender", END)

# 5) Compilamos el grafo, lo que devuelve una función ejecutable 'graph'
graph = builder.compile()

"""
NOTA SOBRE EL FLUJO:

- START -> activity_collector_node
    Se encarga de procesar/etiquetar la última actividad o mensaje del user.
    Actualiza la base de datos y el 'state.activities'.
    Puede guardar un log en conversation_logs.

- analyzer_node
    Lee 'state.activities' y genera un análisis (patrones, tono, etc.). 
    Guarda los resultados en DB y en 'state.analysis'.

- recommender_node
    Produce recomendaciones en base al 'analysis'. Se podría también
    guardar la respuesta en conversation_logs y retomar al final.

Al terminar, 'graph' retorna un state actualizado 
que puedes usar para la siguiente interacción.
"""
