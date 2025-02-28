# zendell/core/graph.py
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List, Dict, Any
from zendell.agents.activity_collector import activity_collector_node
from zendell.agents.analyzer import analyzer_node
from zendell.agents.recommender import recommender_node

class GlobalState(TypedDict):
    user_id: str
    customer_name: str
    activities: List[Dict[str, str]]
    analysis: Dict[str, Any]
    recommendation: List[str]
    last_message: str
    conversation_context: List[Dict[str, Any]]

builder = StateGraph(GlobalState)
builder.add_node("activity_collector", activity_collector_node)
builder.add_node("analyzer", analyzer_node)
builder.add_node("recommender", recommender_node)
builder.add_edge(START, "activity_collector")
builder.add_edge("activity_collector", "analyzer")
builder.add_edge("analyzer", "recommender")
builder.add_edge("recommender", END)
graph = builder.compile()