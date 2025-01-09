# /core/graph.py

from langgraph.graph import StateGraph, START, END
from typing import TypedDict

# Importamos los agentes (nodos) desde la carpeta agents
from agents.activity_collector import activity_collector_node
from agents.analyzer import analyzer_node
from agents.recommender import recommender_node

# 1) Definimos el schema del estado global que se compartirá entre los nodos
class GlobalState(TypedDict):
    customer_name: str                 # Nombre del usuario
    activities: list[str]              # Lista de actividades recolectadas
    analysis: dict[str, str]           # Resultado del análisis (clave-valor)
    recommendation: list[str]          # Lista de recomendaciones generadas
    reminders: list[str]               # Lista de recordatorios pendientes


# 2) Creamos el grafo usando StateGraph y le pasamos el schema GlobalState
builder = StateGraph(GlobalState)

# 3) Añadimos los nodos (agentes) al grafo
builder.add_node("activity_collector", activity_collector_node)
builder.add_node("analyzer", analyzer_node)
builder.add_node("recommender", recommender_node)

# 4) Definimos las conexiones entre los nodos
builder.add_edge(START, "activity_collector")   # El flujo empieza en activity_collector
builder.add_edge("activity_collector", "analyzer")  # Luego pasa al analyzer
builder.add_edge("analyzer", "recommender")     # Y finalmente al recommender
builder.add_edge("recommender", END)            # Termina el flujo en recommender

# 5) Compilamos el grafo, lo que devuelve una función ejecutable
graph = builder.compile()
