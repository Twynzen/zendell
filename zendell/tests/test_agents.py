# /tests/test_agents.py

# 1) Importamos la función y el State desde el archivo de activity_collector.
from agents.activity_collector import activity_collector_node, State
from agents.analyzer import analyzer_node, State
from agents.recommender import recommender_node, State
from agents.goal_finder import goal_finder_node, State

from datetime import datetime

def test_activity_collector():
    """
    Prueba el nodo (agente) que recopila actividades del usuario.
    Verificamos que actualice el estado correctamente.
    """

    # Estado inicial sin actividades
    initial_state: State = {
        "customer_name": "Daniel",
        "activities": [],
        "last_activity_time": ""
    }

    print(f"\n[TEST] Probando 'activity_collector_node' con estado inicial: {initial_state}")
    
    # Nueva actividad a agregar
    new_activity = "Tomar café"

    # Ejecutamos el nodo con la nueva actividad
    updated_state = activity_collector_node(
        state=initial_state,
        new_activity=new_activity
    )

    print(f"[TEST] Estado actualizado tras agregar actividad '{new_activity}': {updated_state}")

    # Verificamos que la actividad haya sido agregada como un diccionario con tipo
    assert any(activity["activity"] == "Tomar café" for activity in updated_state["activities"]), \
        "La actividad no fue agregada correctamente al estado."

    # Verificamos que se haya registrado la hora de la última actividad
    assert updated_state["last_activity_time"] != "", "No se registró la hora de la actividad."


def test_analyzer_node():
    """
    Prueba el nodo (agente) que analiza las actividades del usuario.
    Verifica que genere un análisis correcto usando el LLM.
    """

    # Estado inicial con actividades de distintos tipos
    initial_state: State = {
        "customer_name": "Daniel",
        "activities": [
            {"activity": "Tomar café", "type": "Ocio"},
            {"activity": "Estudiar Python", "type": "Trabajo"},
            {"activity": "Hacer ejercicio", "type": "Ejercicio"}
        ],
        "analysis": ""
    }

    print(f"\n[TEST] Probando 'analyzer_node' con estado inicial: {initial_state}")

    # Ejecutamos el nodo analyzer
    updated_state = analyzer_node(initial_state)

    print(f"[TEST] Estado actualizado tras ejecutar 'analyzer_node': {updated_state}")

    # Verificamos que el campo 'analysis' se haya llenado
    assert updated_state["analysis"] != "", "El análisis no debería estar vacío."
    print(f"\n[TEST] Análisis generado: {updated_state['analysis']}")

def test_recommender_node():
    """
    Prueba el nodo (agente) que genera recomendaciones.
    Verifica que genere recomendaciones y registre la hora de ejecución.
    """

    # Estado inicial con un análisis ya generado
    initial_state: State = {
        "customer_name": "Daniel",
        "activities": [
            {"activity": "Tomar café", "type": "Ocio"},
            {"activity": "Estudiar Python", "type": "Trabajo"}
        ],
        "analysis": "El usuario está trabajando en mejorar sus habilidades de programación.",
        "recommendation": [],
        "last_recommendation_time": ""
    }

    print(f"\n[TEST] Probando 'recommender_node' con estado inicial: {initial_state}")

    # Ejecutamos el nodo recommender
    updated_state = recommender_node(initial_state)

    print(f"[TEST] Estado actualizado tras ejecutar 'recommender_node': {updated_state}")

    # Verificamos que se hayan generado recomendaciones
    assert len(updated_state["recommendation"]) > 0, "No se generaron recomendaciones."
    print(f"\n[TEST] Recomendaciones generadas: {updated_state['recommendation']}")

    # Verificamos que se haya registrado la hora de la última recomendación
    assert updated_state["last_recommendation_time"] != "", "No se registró la hora de la recomendación."
    try:
        datetime.fromisoformat(updated_state["last_recommendation_time"])
    except ValueError:
        assert False, "El formato de la hora registrada no es válido."

def test_goal_finder_node_first_interaction():
    """
    Prueba el nodo 'goal_finder' en su primera interacción con el usuario.
    Verificamos que solicite información general y actualice el estado.
    """

    initial_state: State = {
        "customer_name": None,
        "general_info": {},
        "short_term_info": [],
        "last_interaction_time": ""
    }

    print(f"\n[TEST] Probando 'goal_finder_node' en la primera interacción con estado inicial: {initial_state}")

    # Ejecutamos el nodo goal_finder
    updated_state = goal_finder_node(initial_state)

    print(f"[TEST] Estado actualizado tras la primera interacción: {updated_state}")

    # Verificamos que se haya solicitado información general
    assert "respuesta_inicial" in updated_state["general_info"], "No se solicitó información general al usuario."
    assert updated_state["customer_name"] == "Desconocido", "El nombre temporal no fue establecido correctamente."

    # Verificamos que se haya registrado la hora de la última interacción
    assert updated_state["last_interaction_time"] != "", "No se registró la hora de la interacción."


def test_goal_finder_node_follow_up():
    """
    Prueba el nodo 'goal_finder' en una interacción posterior con el usuario.
    Verificamos que solicite información a corto plazo y actualice el estado.
    """

    initial_state: State = {
        "customer_name": "Daniel",
        "general_info": {
            "nombre": "Daniel",
            "sueños": "Ser un gran desarrollador de IA",
            "hobbies": ["Videojuegos", "Programación", "Leer"]
        },
        "short_term_info": ["Tomar café", "Estudiar Python"],
        "last_interaction_time": ""
    }

    print(f"\n[TEST] Probando 'goal_finder_node' en una interacción posterior con estado inicial: {initial_state}")

    # Ejecutamos el nodo goal_finder
    updated_state = goal_finder_node(initial_state)

    print(f"[TEST] Estado actualizado tras la interacción posterior: {updated_state}")

    # Verificamos que se haya solicitado información a corto plazo
    assert len(updated_state["short_term_info"]) > 2, "No se solicitó información a corto plazo al usuario."

    # Verificamos que se haya registrado la hora de la última interacción
    assert updated_state["last_interaction_time"] != "", "No se registró la hora de la interacción."