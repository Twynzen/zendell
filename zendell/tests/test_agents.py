# /tests/test_agents.py

import pytest
from unittest.mock import MagicMock
from datetime import datetime
from typing import Dict, Any

# -------------------------------------------------------------------------
# Importamos los agentes y su State
# -------------------------------------------------------------------------
from agents.activity_collector import activity_collector_node, State as ActivityCollectorState
from agents.analyzer import analyzer_node, State as AnalyzerState
from agents.recommender import recommender_node, State as RecommenderState

# Ojo: Este goal_finder usa un State distinto
from agents.goal_finder import goal_finder_node, State as GoalFinderState
from core.utils import get_timestamp


# =============================================================================
#                               FIXTURES
# =============================================================================
@pytest.fixture
def db_manager_mock():
    """
    Mock de un posible db_manager que expone 'get_state' y 'save_state'.
    Lo usaremos en todos los tests para simular acceso a la BD.
    """
    mock = MagicMock()

    # Por default, si no se especifica, que get_state retorne un dict vacío
    # o algo que el agente pueda usar. Luego en cada test lo personalizamos.
    mock.get_state.return_value = {}
    return mock


# =============================================================================
#                 TESTS PARA EL ACTIVITY_COLLECTOR
# =============================================================================
def test_activity_collector(db_manager_mock):
    """
    Prueba el nodo (agente) que recopila actividades del usuario.
    Verificamos que actualice el estado correctamente, y simulamos
    un guardado en BD (si lo necesitáramos).
    """
    # Supongamos que este agente también leyera un 'ActivityCollectorState' de la BD.
    # Podemos mockear que la BD ya tiene cierto estado.
    fake_db_state: ActivityCollectorState = {
        "customer_name": "Daniel",
        "activities": [
            {"activity": "Leer documentación", "type": "Trabajo"}
        ],
        "last_activity_time": ""
    }
    db_manager_mock.get_state.return_value = fake_db_state

    print(f"{get_timestamp()}",f"\n[TEST] Probando 'activity_collector_node' con estado (BD) inicial: {fake_db_state}")

    # Nueva actividad a agregar
    new_activity = "Tomar café"

    # Llamamos la función de la forma habitual, aunque no esté param. para db_manager
    updated_state = activity_collector_node(
        state=fake_db_state,
        new_activity=new_activity
    )

    print(f"{get_timestamp()}",f"[TEST] Estado actualizado tras agregar actividad '{new_activity}': {updated_state}")

    # Verificamos que se haya agregado la nueva actividad
    assert any(
        activity["activity"] == "Tomar café"
        for activity in updated_state["activities"]
    ), "La actividad no fue agregada correctamente al estado."

    assert updated_state["last_activity_time"] != "", "No se registró la hora de la actividad."

    # En un mundo real, tal vez quisiéramos guardar de nuevo en la BD:
    db_manager_mock.save_state.assert_not_called()  # Este agente no lo hace por ahora, pero si se hiciera, verificaríamos.


# =============================================================================
#                   TESTS PARA EL ANALYZER NODE
# =============================================================================
def test_analyzer_node(db_manager_mock):
    """
    Prueba el nodo (agente) que analiza las actividades del usuario.
    Verifica que genere un análisis correcto usando el LLM.
    """

    # Estado inicial de BD con actividades de distintos tipos
    fake_db_state: AnalyzerState = {
        "customer_name": "Daniel",
        "activities": [
            {"activity": "Tomar café", "type": "Ocio"},
            {"activity": "Estudiar Python", "type": "Trabajo"},
            {"activity": "Hacer ejercicio", "type": "Ejercicio"}
        ],
        "analysis": ""
    }
    db_manager_mock.get_state.return_value = fake_db_state

    print(f"{get_timestamp()}",f"\n[TEST] Probando 'analyzer_node' con estado (BD) inicial: {fake_db_state}")

    # Ejecutamos el nodo analyzer
    updated_state = analyzer_node(fake_db_state)

    print(f"{get_timestamp()}",f"[TEST] Estado actualizado tras ejecutar 'analyzer_node': {updated_state}")

    # Verificamos que el campo 'analysis' se haya llenado
    assert updated_state["analysis"] != "", "El análisis no debería estar vacío."
    print(f"{get_timestamp()}",f"\n[TEST] Análisis generado: {updated_state['analysis']}")


# =============================================================================
#                   TESTS PARA EL RECOMMENDER NODE
# =============================================================================
def test_recommender_node(db_manager_mock):
    """
    Prueba el nodo (agente) que genera recomendaciones.
    Verifica que genere recomendaciones y registre la hora de ejecución.
    """

    # Estado inicial con un análisis ya generado
    fake_db_state: RecommenderState = {
        "customer_name": "Daniel",
        "activities": [
            {"activity": "Tomar café", "type": "Ocio"},
            {"activity": "Estudiar Python", "type": "Trabajo"}
        ],
        "analysis": "El usuario está trabajando en mejorar sus habilidades de programación.",
        "recommendation": [],
        "last_recommendation_time": ""
    }
    db_manager_mock.get_state.return_value = fake_db_state

    print(f"{get_timestamp()}",f"\n[TEST] Probando 'recommender_node' con estado (BD) inicial: {fake_db_state}")

    # Ejecutamos el nodo recommender
    updated_state = recommender_node(fake_db_state)

    print(f"{get_timestamp()}",f"[TEST] Estado actualizado tras ejecutar 'recommender_node': {updated_state}")

    # Verificamos que se hayan generado recomendaciones
    assert len(updated_state["recommendation"]) > 0, "No se generaron recomendaciones."
    print(f"{get_timestamp()}",f"\n[TEST] Recomendaciones generadas: {updated_state['recommendation']}")

    # Verificamos que se haya registrado la hora de la última recomendación
    assert updated_state["last_recommendation_time"] != "", "No se registró la hora de la recomendación."
    try:
        datetime.fromisoformat(updated_state["last_recommendation_time"])
    except ValueError:
        assert False, "El formato de la hora registrada no es válido."


# =============================================================================
#               TESTS PARA EL GOAL FINDER (CON DB MANAGER)
# =============================================================================
def test_goal_finder_node_first_interaction(db_manager_mock):
    """
    Prueba el nodo 'goal_finder' en su primera interacción con el usuario.
    Verificamos que solicite información general y actualice el estado en la BD.
    """

    # Simulamos que la BD no tiene registro previo (primera vez del usuario)
    db_manager_mock.get_state.return_value = {
        "customer_name": None,
        "general_info": {},
        "short_term_info": [],
        "last_interaction_time": "",
        "daily_interaction_count": 0,      # Nuevo
        "last_interaction_date": ""        # Nuevo
    }

    # user_id ficticio
    user_id = "test_user_001"

    print(f"{get_timestamp()}",f"\n[TEST] Probando 'goal_finder_node' primera interacción (user_id={user_id})")

    updated_state = goal_finder_node(
        user_id=user_id,
        db_manager=db_manager_mock,
        hours_between_interactions=0,       # forzamos la interacción inmediata
        max_daily_interactions=16
    )

    print(f"{get_timestamp()}",f"[TEST] Estado actualizado tras la primera interacción: {updated_state}")

    # Verificamos que se haya solicitado información general
    assert "respuesta_inicial" in updated_state["general_info"], "No se solicitó información general al usuario."
    assert updated_state["customer_name"] == "Desconocido", "El nombre temporal no fue establecido correctamente."

    # Verificamos que se haya registrado la hora de la última interacción
    assert updated_state["last_interaction_time"] != "", "No se registró la hora de la interacción."

    # Debió guardarse en la BD
    db_manager_mock.save_state.assert_called_once()
    args, _ = db_manager_mock.save_state.call_args
    assert args[0] == user_id, "El user_id enviado a la BD no coincide."
    saved_state = args[1]
    assert saved_state["customer_name"] == "Desconocido", "Se debió guardar 'Desconocido' en la BD."


def test_goal_finder_node_follow_up(db_manager_mock):
    db_manager_mock.get_state.return_value = {
        "customer_name": "Daniel",
        "general_info": {
            "nombre": "Daniel",
            "ocupacion": "Desarrollador",
            "sueños": "Ser un gran desarrollador de IA",
            "hobbies": ["Videojuegos", "Programación", "Leer"]
        },
        "short_term_info": ["Tomar café", "Estudiar Python"],
        "last_interaction_time": "",
        "daily_interaction_count": 5,      # Ejemplo: lleva 5 interacciones hoy
        "last_interaction_date": "2025-01-11"  # <-- Ajustado a la fecha actual del Goal Finder
    }

    user_id = "test_user_002"
    updated_state = goal_finder_node(
        user_id=user_id,
        db_manager=db_manager_mock,
        hours_between_interactions=0,
        max_daily_interactions=16
    )

    # Checamos que haya agregado la nueva respuesta
    assert len(updated_state["short_term_info"]) > 2
    # Verificamos la hora
    assert updated_state["last_interaction_time"] != ""
    # Verificamos que haya subido de 5 a 6
    assert updated_state["daily_interaction_count"] == 6, \
        "El contador diario de interacciones no se incrementó correctamente."
    
    db_manager_mock.save_state.assert_called_once()
