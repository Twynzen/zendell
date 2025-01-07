# /agents/activity_collector.py

# 1) Importamos TypedDict para definir la "forma" (schema) del estado,
# y Optional/List si requerimos usar listas u opciones en el estado.
from typing import TypedDict, Optional, List

# 2) Definimos la clase "State" que extiende TypedDict.
#    Aquí especificamos qué datos estaremos manejando.
#    En este caso, "my_var", "customer_name" y "activities".
#    "activities" será una lista donde iremos guardando
#    lo que vayamos "recolectando".
class State(TypedDict):
    my_var: str
    customer_name: str
    activities: List[str]

# 3) Esta función es el nodo (agente) que recolecta
#    o actualiza la información del usuario.
#    - "state" es el estado actual
#    - "new_activity" es la actividad que queremos
#      añadir a la lista (por ejemplo, "Tomar café", "Estudiar Python", etc.).
def activity_collector_node(
    state: State,
    new_activity: Optional[str] = None
) -> State:
    """
    Recolecta la actividad (si viene) y la registra en el estado.
    """

    # 3.1) Si el "activities" no existe (o viene vacío),
    #      inicializamos la lista. (En teoría con TypedDict,
    #      ya lo definimos, pero es buena práctica chequear).
    if "activities" not in state or state["activities"] is None:
        state["activities"] = []

    # 3.2) Si recibimos una actividad nueva, la agregamos
    #      a la lista de actividades.
    if new_activity:
        state["activities"].append(new_activity)

    # 3.3) Podemos modificar otras partes del estado, por ejemplo "my_var".
    #      Podríamos usarlo como una especie de "debug" o "mensaje".
    state["my_var"] = "Activity collector updated the list."

    # 3.4) Retornamos el estado actualizado para que el grafo
    #      o siguiente agente lo procese.
    return state
