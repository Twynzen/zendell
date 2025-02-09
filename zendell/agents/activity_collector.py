# zendell/agents/activity_collector.py

import json
import re
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
    
    # Actualizamos el perfil solo en las etapas iniciales.
    if st.get("conversation_stage", "initial") in ["initial", "ask_profile"]:
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
    else:
        print("[activity_collector] Omite actualizar perfil; se trata de una actividad.")

    if "short_term_info" not in st:
        st["short_term_info"] = []
    st["short_term_info"].append(f"[User] {last_msg}")
    
    stage = st.get("conversation_stage", "initial")
    # Solo se generan actividades en etapas de actividades
    if stage not in ["ask_last_hour", "ask_next_hour"]:
        db.save_state(user_id, st)
        return global_state

    tc = "future" if stage == "ask_next_hour" else "past"
    category = classify_activity(last_msg)
    print(f"[activity_collector] Actividad clasificada como: {category}")
    
    subs = extract_sub_activities(last_msg)
    print(f"[activity_collector] Sub-actividades extraídas: {subs}")
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
        # Prompt de clarificación actualizado para forzar salida JSON
        prompt_clarify = (
            f"El usuario escribió: '{last_msg}'. Se ha registrado la actividad: '{item['title']}' "
            f"con la categoría '{item['category']}'. "
            "Analiza el mensaje y, si detectas que el usuario está cuestionando (por ejemplo, frases como '¿por qué me preguntas eso?', '¿para qué me preguntas eso?', etc.), "
            "incluye una breve explicación del motivo de la pregunta. Luego, genera al menos dos preguntas de clarificación que ayuden a entender mejor la actividad. "
            "Devuelve **únicamente** un JSON válido con el siguiente formato EXACTO:\n"
            '{"questions": ["Pregunta 1", "Pregunta 2", ...]}\n'
            "Si no hay preguntas que hacer, devuelve: {\"questions\": []}."
        )
        response = ask_gpt(prompt_clarify)
        try:
            data = json.loads(response)
            questions = data.get("questions", [])
        except Exception as e:
            print(f"[activity_collector] Error al parsear preguntas: {e}")
            questions = []
        item["clarification_questions"] = questions
        
        new_items.append(item)
        db.add_activity(user_id, item)
        print(f"[activity_collector] Actividad agregada: {item}")
    
    if new_items:
        llm_prompt = f"El mensaje '{last_msg}' generó las siguientes actividades: {new_items}. Explica detalladamente por qué se detectaron estas actividades y qué elementos permitieron identificarlas."
    else:
        llm_prompt = f"El mensaje '{last_msg}' no generó actividades. Razona detalladamente por qué no se detectaron actividades y qué elementos faltaron."
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
    prompt = (
        "Extrae de forma detallada la siguiente información del usuario, en formato JSON con las claves "
        '{"name", "ocupacion", "gustos", "metas"}:\n'
        "1. name: Si el usuario se presenta, extrae su nombre o nombre completo.\n"
        "2. ocupacion: Extrae la ocupación o profesión si se menciona.\n"
        "3. gustos: Extrae sus gustos o aficiones, pero evita confundir actividades con gustos.\n"
        "4. metas: Extrae cualquier objetivo o meta que mencione.\n"
        "Si algún dato no está presente, asigna una cadena vacía.\n"
        f"Mensaje: {msg}"
    )
    r = ask_gpt(prompt)
    out = {"name": "", "ocupacion": "", "gustos": "", "metas": ""}
    if not r:
        return out
    try:
        match = re.search(r'\{.*\}', r, re.DOTALL)
        if match:
            json_str = match.group(0)
            data = json.loads(json_str)
        else:
            data = json.loads(r)
        for k in out:
            out[k] = data.get(k, "").strip()
    except Exception as e:
        print(f"[extract_profile_info] Error parsing JSON: {e}")
    return out

def classify_activity(msg: str) -> str:
    prompt = (
        f"Analiza el siguiente mensaje: '{msg}'. "
        "Determina la categoría de la actividad descrita de manera flexible basándote en el contexto y la intención. "
        "Devuelve **únicamente** un JSON válido con la clave 'category' en el siguiente formato EXACTO:\n"
        '{"category": "La categoría que corresponda"}\n'
        "Si no se identifica actividad, devuelve: {\"category\": \"NoActivity\"}."
    )
    r = ask_gpt(prompt)
    if not r:
        return "NoActivity"
    try:
        data = json.loads(r)
        category = data.get("category", "NoActivity")
        return category.strip()
    except Exception as e:
        print(f"[classify_activity] Error: {e}")
        return "NoActivity"

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
