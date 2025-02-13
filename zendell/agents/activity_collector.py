# zendell/agents/activity_collector.py

import json
import re
from datetime import datetime
from zendell.services.llm_provider import ask_gpt
from zendell.core.db import MongoDBManager

def activity_collector_node(global_state: dict) -> dict:
    user_id = global_state.get("user_id", "")
    last_msg = global_state.get("last_message", "")
    if not last_msg:
        return global_state
    db = MongoDBManager()
    st = db.get_state(user_id)
    if st.get("conversation_stage", "initial") in ["initial", "ask_profile"]:
        extracted = extract_profile_info(last_msg)
        if extracted.get("name"):
            st["name"] = extracted["name"]
        st.setdefault("general_info", {})
        gi = st["general_info"]
        if extracted.get("ocupacion"):
            gi["ocupacion"] = extracted["ocupacion"]
        if extracted.get("gustos"):
            gi["gustos"] = extracted["gustos"]
        if extracted.get("metas"):
            gi["metas"] = extracted["metas"]
    st.setdefault("short_term_info", []).append(f"[User] {last_msg}")
    stage = st.get("conversation_stage", "initial")
    if stage not in ["ask_last_hour", "ask_next_hour"]:
        db.save_state(user_id, st)
        return global_state
    tc = "future" if stage == "ask_next_hour" else "past"
    category = classify_activity(last_msg)
    subs = extract_sub_activities(last_msg)
    if not subs:
        filtered_msg = re.split(r'\?', last_msg)[-1].strip() or last_msg
        default_title = " ".join(filtered_msg.split()[:5]) if filtered_msg.split() else "Actividad"
        default_activity = {
            "title": default_title,
            "category": category,
            "time_context": tc,
            "timestamp": datetime.utcnow().isoformat(),
            "original_message": last_msg,
            "clarification_questions": [],
            "clarifier_responses": []
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
            "clarification_questions": [],
            "clarifier_responses": []
        }
        prompt_clarify = (
            f"Analiza el mensaje: '{last_msg}'. Considera la actividad descrita como '{item['title']}' y utiliza los detalles del contexto para generar una pregunta de clarificación específica y razonada. "
            "La pregunta debe invitar al usuario a profundizar en aspectos relevantes de esa actividad sin ser genérica. Devuelve únicamente un JSON válido EXACTAMENTE en el siguiente formato (sin texto adicional): "
            '{"questions": ["Pregunta 1", "Pregunta 2", ...]} '
            "Si no se pueden generar preguntas razonadas, devuelve: {\"questions\": []}."
        )
        response = ask_gpt(prompt_clarify)
        try:
            data = json.loads(response)
            questions = data.get("questions", [])
            if not questions:
                raise ValueError
        except Exception:
            fallback_prompt = (
                f"El mensaje '{last_msg}' menciona la actividad '{item['title']}'. Utilizando el contexto, genera al menos una pregunta de clarificación específica que indague en los detalles relevantes de esta actividad. "
                "Devuelve únicamente un JSON válido EXACTAMENTE en el siguiente formato (sin texto adicional): "
                '{"questions": ["Pregunta 1", "Pregunta 2", ...]}'
            )
            fallback_response = ask_gpt(fallback_prompt)
            try:
                data = json.loads(fallback_response)
                questions = data.get("questions", [])
                if not questions:
                    raise ValueError
            except Exception:
                questions = [f"¿Podrías detallar más sobre la actividad '{item['title']}' mencionada en el mensaje?"]
        item["clarification_questions"] = questions
        new_items.append(item)
        db.add_activity(user_id, item)
    llm_prompt = (f"El mensaje '{last_msg}' generó las siguientes actividades: {new_items}. Explica por qué se detectaron estas actividades y qué elementos permitieron identificarlas." if new_items else f"El mensaje '{last_msg}' no generó actividades. Razona por qué no se detectaron actividades y qué elementos faltaron.")
    reasoning = ask_gpt(llm_prompt)
    st.setdefault("interaction_history", []).append({
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
    elif stage == "ask_next_hour":
        st.setdefault("activities_next_hour", []).append({
            "timestamp": datetime.utcnow().isoformat(),
            "activities": new_items,
            "llm_reasoning": reasoning
        })
    db.save_state(user_id, st)
    global_state["activities"].extend(new_items)
    return global_state

def extract_profile_info(msg: str) -> dict:
    prompt = (
        "Extrae de forma detallada la siguiente información del usuario, en formato JSON con las claves {\"name\", \"ocupacion\", \"gustos\", \"metas\"}: "
        "1. name: Si el usuario se presenta, extrae su nombre o nombre completo. "
        "2. ocupacion: Extrae la ocupación o profesión si se menciona. "
        "3. gustos: Extrae sus gustos o aficiones, pero evita confundir actividades con gustos. "
        "4. metas: Extrae cualquier objetivo o meta que mencione. "
        "Si algún dato no está presente, asigna una cadena vacía. "
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
    except Exception:
        pass
    return out

def classify_activity(msg: str) -> str:
    prompt = (
        f"Analiza el siguiente mensaje: '{msg}'. Determina la categoría de la actividad descrita basándote en el contexto y la intención. "
        "Devuelve únicamente un JSON válido EXACTAMENTE en el siguiente formato (sin texto adicional): "
        '{"category": "La categoría que corresponda"} '
        "Si no se identifica actividad, devuelve: {\"category\": \"NoActivity\"}."
    )
    r = ask_gpt(prompt)
    if not r:
        return "NoActivity"
    try:
        data = json.loads(r)
        category = data.get("category", "NoActivity")
        return category.strip()
    except Exception:
        return "NoActivity"

def extract_sub_activities(msg: str) -> list:
    prompt = (
        f"Analiza el siguiente mensaje: '{msg}'. Extrae todas las actividades distintas que se describen en el mensaje. "
        "Cada actividad debe incluir un título, una categoría sugerida y un contexto temporal ('past' o 'future'). "
        "Devuelve únicamente un JSON válido EXACTAMENTE en el siguiente formato (sin texto adicional): "
        '{"activities": [{"title": "Descripción de la actividad", "category": "Categoría sugerida", "time_context": "past"}]} '
        "Si no se puede extraer una actividad clara, devuelve: {\"activities\": []}."
    )
    r = ask_gpt(prompt)
    if not r:
        return []
    r = r.replace("`json", "").replace("`", "").strip()
    try:
        data = json.loads(r)
        return data.get("activities", [])
    except Exception:
        return []
