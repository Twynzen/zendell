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
    extracted = extract_profile_info(last_msg)
    print(f"[activity_collector] Perfil extraído: {extracted}")
    if extracted["name"]:
        st["name"] = extracted["name"]
    if "general_info" not in st:
        st["general_info"] = {}
    gi = st["general_info"]
    gi["ocupacion"] = extracted["ocupacion"] or gi.get("ocupacion", "")
    gi["gustos"] = extracted["gustos"] or gi.get("gustos", "")
    gi["metas"] = extracted["metas"] or gi.get("metas", "")
    category = classify_activity(last_msg)
    print(f"[activity_collector] Actividad clasificada como: {category}")
    subs = extract_sub_activities(last_msg)
    print(f"[activity_collector] Sub-actividades extraídas: {subs}")
    new_items = []
    for a in subs:
        item = {
            "title": a.get("title", ""),
            "category": a.get("category", ""),
            "time_context": a.get("time_context", "past"),
            "timestamp": datetime.utcnow().isoformat(),
            "original_message": last_msg
        }
        new_items.append(item)
        db.add_activity(user_id, item)
        print(f"[activity_collector] Actividad agregada: {item}")
    if new_items:
        llm_prompt = f"El mensaje '{last_msg}' generó las siguientes actividades: {new_items}. Explica detalladamente por qué se detectaron estas actividades y qué elementos en el mensaje permitieron identificarlas."
    else:
        llm_prompt = f"El mensaje '{last_msg}' no generó actividades. Razona detalladamente por qué no se detectaron actividades y qué elementos del mensaje faltaron o no fueron interpretados como actividad."
    reasoning = ask_gpt(llm_prompt)
    print(f"[activity_collector] Razonamiento del LLM: {reasoning}")
    if "interaction_history" not in st:
        st["interaction_history"] = []
    if new_items:
        st["interaction_history"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "activities": new_items,
            "llm_reasoning": reasoning
        })
    if "short_term_info" not in st:
        st["short_term_info"] = []
    st["short_term_info"].append(f"[User] {last_msg}")
    stage = st.get("conversation_stage", "initial")
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
