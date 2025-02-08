# zendell/agents/activity_collector.py

import json
from datetime import datetime
from zendell.services.llm_provider import ask_gpt
from zendell.core.db import MongoDBManager

def activity_collector_node(global_state: dict) -> dict:
    user_id = global_state.get("user_id", "")
    last_msg = global_state.get("last_message", "")
    print(f"[activity_collector] Mensaje recibido: {last_msg}")
    if not last_msg:
        return global_state
    db = MongoDBManager()
    st = db.get_state(user_id)
    # Extraer información de perfil y actualizar solo si se obtiene valor
    extracted = extract_profile_info(last_msg)
    print(f"[activity_collector] Perfil extraído: {extracted}")
    if extracted.get("name"):
        st["name"] = extracted["name"]
    if "general_info" not in st:
        st["general_info"] = {}
    gi = st["general_info"]
    if extracted.get("ocupacion"):
        gi["ocupacion"] = extracted["ocupacion"]
    if extracted.get("gustos"):
        gi["gustos"] = extracted["gustos"]
    if extracted.get("metas"):
        gi["metas"] = extracted["metas"]
    if "short_term_info" not in st:
        st["short_term_info"] = []
    st["short_term_info"].append(f"[User] {last_msg}")
    
    stage = st.get("conversation_stage", "initial")
    # Solo se generan actividades en las etapas de "ask_last_hour" y "ask_next_hour"
    if stage not in ["ask_last_hour", "ask_next_hour"]:
        db.save_state(user_id, st)
        return global_state

    tc = "future" if stage == "ask_next_hour" else "past"
    category = classify_activity(last_msg)
    print(f"[activity_collector] Actividad clasificada como: {category}")
    
    subs = extract_sub_activities(last_msg)
    print(f"[activity_collector] Sub-actividades extraídas: {subs}")
    # Si no se obtuvieron subactividades, se crea una actividad por defecto
    if not subs:
        default_title = " ".join(last_msg.split()[:3]) if last_msg.split() else "Actividad"
        default_activity = {
            "title": default_title,
            "category": category,
            "time_context": tc,
            "timestamp": datetime.utcnow().isoformat(),
            "original_message": last_msg,
            "clarification_questions": []
        }
        subs = [default_activity]
    
    new_items = []
    for sub in subs:
        item = {
            "title": sub.get("title", ""),
            "category": sub.get("category", category),
            "time_context": sub.get("time_context", tc),
            "timestamp": datetime.utcnow().isoformat(),
            "original_message": last_msg,
            "clarification_questions": []
        }
        # Generar preguntas de clarificación para la actividad
        prompt_clarify = (
            f"El usuario dijo: '{last_msg}'. Se ha registrado la actividad: '{item['title']}' "
            f"en la categoría '{item['category']}'. Dado que el mensaje puede ser ambiguo, "
            "genera preguntas de clarificación que ayuden a indagar más en detalles de esta actividad. "
            "Por ejemplo, si la actividad es 'Trabajé en un proyecto de python', podrías preguntar: "
            "'¿Qué tareas específicas realizaste?', '¿Cuál fue el objetivo del proyecto?', etc. "
            "Devuelve la lista en formato JSON con la clave 'questions'."
        )
        response = ask_gpt(prompt_clarify)
        try:
            data = json.loads(response)
            questions = data.get("questions", [])
        except Exception:
            questions = []
        item["clarification_questions"] = questions
        
        new_items.append(item)
        db.add_activity(user_id, item)
        print(f"[activity_collector] Actividad agregada: {item}")
    
    # Generar razonamiento global del LLM para registro
    if new_items:
        llm_prompt = f"El mensaje '{last_msg}' generó las siguientes actividades: {new_items}. Explica detalladamente por qué se detectaron estas actividades y qué elementos en el mensaje permitieron identificarlas."
    else:
        llm_prompt = f"El mensaje '{last_msg}' no generó actividades. Razona detalladamente por qué no se detectaron actividades y qué elementos del mensaje faltaron o no fueron interpretados como actividad."
    reasoning = ask_gpt(llm_prompt)
    print(f"[activity_collector] Razonamiento del LLM: {reasoning}")
    
    if "interaction_history" not in st:
        st["interaction_history"] = []
    st["interaction_history"].append({
        "timestamp": datetime.utcnow().isoformat(),
        "activities": new_items,
        "llm_reasoning": reasoning
    })
    
    if stage == "ask_last_hour":
        st.setdefault("activities_last_hour", []).append({
            "timestamp": datetime.utcnow().isoformat(),
            "activities": new_items,
            "llm_reasoning": reasoning
        })
        print("[activity_collector] Guardando actividades de la última hora en DB")
    elif stage == "ask_next_hour":
        st.setdefault("activities_next_hour", []).append({
            "timestamp": datetime.utcnow().isoformat(),
            "activities": new_items,
            "llm_reasoning": reasoning
        })
        print("[activity_collector] Guardando actividades de la próxima hora en DB")
    
    db.save_state(user_id, st)
    global_state["activities"].extend(new_items)
    return global_state

def extract_profile_info(msg: str) -> dict:
    prompt = f'Texto del usuario: "{msg}" Extrae en JSON: {{"name":"","ocupacion":"","gustos":"","metas":""}}'
    r = ask_gpt(prompt)
    out = {"name": "", "ocupacion": "", "gustos": "", "metas": ""}
    if not r:
        return out
    r = r.replace("`json", "").replace("`", "").strip()
    try:
        data = json.loads(r)
        for k in out:
            out[k] = data.get(k, "")
    except:
        pass
    return out

def classify_activity(msg: str) -> str:
    prompt = f'Texto: "{msg}" ¿Describe una actividad? Responde con uno de [Trabajo, Descanso, Ejercicio, Ocio, Otro, NoActivity].'
    r = ask_gpt(prompt)
    if not r:
        return "NoActivity"
    r = r.strip()
    valids = ["Trabajo", "Descanso", "Ejercicio", "Ocio", "Otro", "NoActivity"]
    return r if r in valids else "NoActivity"

def extract_sub_activities(msg: str) -> list:
    prompt = f'Texto: "{msg}" Enumera en JSON las subactividades como: {{"activities": [{{"title":"","category":"","time_context":"past"}}]}}'
    r = ask_gpt(prompt)
    if not r:
        return []
    r = r.replace("`json", "").replace("`", "").strip()
    try:
        data = json.loads(r)
        return data.get("activities", [])
    except:
        return []
