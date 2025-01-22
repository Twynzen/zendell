# /agents/activity_collector.py

from typing import TypedDict, Optional, List, Dict
from services.llm_provider import ask_gpt
from datetime import datetime
import json

class State(TypedDict):
    customer_name: str
    activities: List[Dict[str, str]]
    last_activity_time: str
    connected_channel: str
    last_connection_info: str

def activity_collector_node(
    state: dict,
    new_activity: Optional[str] = None,
    channel_info: Optional[str] = None
) -> dict:
    if "activities" not in state or state["activities"] is None:
        state["activities"] = []

    if new_activity:
        # (A) Mejoramos el prompt con ejemplos de tristeza, etc.
        prompt = (
            f"""El usuario escribió: "{new_activity}". 
1) Determina la categoría de la actividad: [Trabajo, Descanso, Ejercicio, Ocio, Otro].
2) Determina el estado de ánimo aproximado del usuario. 
   Usa estas posibles etiquetas: [positivo, neutral, negativo, enojado, cansado, triste].
   Considera que si menciona "triste", "depre", "deprimido", "dolido", "decaído", etc., 
   lo clasifiques como "triste" o "negativo", NO "neutral".
3) Responde en formato JSON. Ejemplo: {{"type": "Ocio", "mood": "positivo"}}.
"""
        )

        print("[DEBUG] Llamando a ask_gpt para clasificar la actividad y mood...")
        response = ask_gpt(prompt)
        print(f"[DEBUG] Respuesta de ask_gpt: {response}")

        # (B) Parseamos la respuesta JSON
        try:
            data = json.loads(response)
            activity_type = data.get("type", "Otro")
            mood = data.get("mood", "neutral")
        except:
            activity_type = "Otro"
            mood = "neutral"

        # (C) Fallback manual: si detectamos palabras clave negativas en el texto
        #    y el LLM no lo marcó como "negativo" o "triste", forzamos.
        lowered = new_activity.lower()
        negative_keywords = ["triste", "depre", "deprim", "dolido", "mal", "decaido", "cansado", "no quiero hablar"]
        # Nota: "deprim" para cubrir "deprimido"/"deprimida"
        for kw in negative_keywords:
            if kw in lowered and mood not in ["negativo", "triste"]:
                mood = "triste"  # o "negativo"
                break
        
        # (D) Guardamos en 'activities' algo más estructurado
        state["activities"].append({
            "activity": new_activity,
            "type": activity_type,
            "mood": mood
        })

    # (E) Actualizamos timestamp e info de canal
    state["last_activity_time"] = datetime.now().isoformat()
    
    if channel_info:
        state["connected_channel"] = channel_info
        state["last_connection_info"] = f"Conexión registrada a las {state['last_activity_time']} en {channel_info}"

    return state
