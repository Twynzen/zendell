# /tests/test_agents.py

# 1) Importamos la función y el State desde el archivo de activity_collector.
from agents.activity_collector import activity_collector_node, State

# 2) Definimos una función de prueba: "test_activity_collector"
def test_activity_collector():
    """
    Prueba el nodo (agente) que recopila actividades del usuario.
    Verificamos que actualice el estado correctamente.
    """

    # 2.1) Creamos un estado inicial:
    #      - my_var vacío (o algún texto).
    #      - customer_name "Daniel"
    #      - activities como lista vacía.
    initial_state: State = {
        "my_var": "",
        "customer_name": "Daniel",
        "activities": []
    }

    # 2.2) Llamamos a nuestra función con una actividad nueva.
    updated_state = activity_collector_node(
        state=initial_state,
        new_activity="Tomar café"
    )

    # 2.3) Verificamos (assert) que la actividad haya sido agregada.
    assert "Tomar café" in updated_state["activities"], \
        "La actividad no fue agregada correctamente al estado."

    # 2.4) Verificamos que "my_var" se cambie.
    assert updated_state["my_var"] == "Activity collector updated the list.", \
        "La variable 'my_var' no fue actualizada como se esperaba."
