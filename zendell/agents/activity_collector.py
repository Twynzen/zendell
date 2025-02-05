# zendell/agents/activity_collector.py

from typing import Dict, Any
from datetime import datetime
from zendell.services.llm_provider import ask_gpt
from zendell.core.db import MongoDBManager
import json

def activity_collector_node(global_state: Dict[str, Any]) -> Dict[str, Any]:
    user_id = global_state.get("user_id", "")
    last_msg = global_state.get("last_message", "")
    if not last_msg:
        return global_state
    db = MongoDBManager()
    st = db.get_state(user_id)
    extracted = extract_profile_info(last_msg)
    if extracted["name"]:
        st["name"] = extracted["name"]
    if "general_info" not in st:
        st["general_info"] = {}
    gi = st["general_info"]
    gi["ocupacion"] = extracted["ocupacion"] or gi.get("ocupacion","")
    gi["gustos"] = extracted["gustos"] or gi.get("gustos","")
    gi["metas"] = extracted["metas"] or gi.get("metas","")
    category = classify_activity(last_msg)
    subs = extract_sub_activities(last_msg)
    new_items = []
    for a in subs:
        item = {
            "title": a.get("title",""),
            "category": a.get("category",""),
            "time_context": a.get("time_context","past"),
            "timestamp": datetime.utcnow().isoformat(),
            "original_message": last_msg
        }
        new_items.append(item)
        db.add_activity(user_id, item)
    if "interaction_history" not in st:
        st["interaction_history"] = []
    if new_items:
        st["interaction_history"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "activities": new_items
        })
    if "short_term_info" not in st:
        st["short_term_info"] = []
    st["short_term_info"].append(f"[User] {last_msg}")
    db.save_state(user_id, st)
    return global_state

def extract_profile_info(msg: str) -> dict:
    prompt = f'Texto del usuario: "{msg}" Extrae en JSON: {{"name":"","ocupacion":"","gustos":"","metas":""}}'
    r = ask_gpt(prompt)
    out = {"name":"","ocupacion":"","gustos":"","metas":""}
    if not r:
        return out
    r = r.replace("`json","").replace("`","").strip()
    try:
        data = json.loads(r)
        for k in out:
            out[k] = data.get(k,"")
    except:
        pass
    return out

def classify_activity(msg: str) -> str:
    prompt = f'Texto: "{msg}" ¿Describe una actividad? Responde con uno de [Trabajo, Descanso, Ejercicio, Ocio, Otro, NoActivity].'
    r = ask_gpt(prompt)
    if not r:
        return "NoActivity"
    r = r.strip()
    valids = ["Trabajo","Descanso","Ejercicio","Ocio","Otro","NoActivity"]
    return r if r in valids else "NoActivity"

def extract_sub_activities(msg: str) -> list:
    prompt = f'Texto: "{msg}" Enumera en JSON las subactividades como: {{"activities": [{{"title":"","category":"","time_context":"past"}}]}}'
    r = ask_gpt(prompt)
    if not r:
        return []
    r = r.replace("`json","").replace("`","").strip()
    try:
        data = json.loads(r)
        return data.get("activities",[])
    except:
        return []
