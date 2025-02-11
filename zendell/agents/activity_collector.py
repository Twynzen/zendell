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
    if stage not in ["ask_last_hour", "ask_next_hour", "clarify"]:
        db.save_state(user_id, st)
        return global_state
    if stage == "clarify":
        activities_next_hour = st.get("activities_next_hour", [])
        if activities_next_hour:
            last_batch = activities_next_hour[-1]
            if last_batch.get("activities"):
                last_activity = last_batch["activities"][-1]
                last_activity["clarification_response"] = last_msg
                print(f"[activity_collector] Actualizada aclaración en la actividad: {last_activity}")
        else:
            print("[activity_collector] No hay actividad previa para actualizar con aclaración.")
        db.save_state(user_id, st)
        return global_state
    tc = "future" if stage == "ask_next_hour" else "past"
    category = classify_activity(last_msg)
    print(f"[activity_collector] Actividad clasificada como: {category}")
    subs = extract_sub_activities(last_msg)
    print(f"[activity_collector] Sub-actividades extraídas: {subs}")
    if not subs:
        filtered_msg = re.split(r'\?', last_msg)[-1].strip() or last_msg
        default_title = " ".join(filtered_msg.split()[:5]) if filtered_msg.split() else "Actividad"
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
        prompt_clarify = (
            f"Analiza el mensaje: '{last_msg}'. De la misma, extrae la parte que describe la actividad "
            f"relacionada con '{item['title']}' y ten en cuenta que el usuario menciona detalles como 'Age of Mythology' o 'Alejandra'. "
            "Genera preguntas de clarificación específicas que sean relevantes a esos detalles. Por ejemplo, si se menciona 'Alejandra', "
            "podrías preguntar '¿Quién es Alejandra para ti?'; si se menciona 'Age of Mythology', pregunta '¿Qué significado tiene para ti ese juego?'. "
            "Además, si el mensaje incluye una pregunta sobre por qué se pregunta sobre estas actividades, incluye una breve explicación del propósito de la pregunta. "
            "Devuelve **únicamente** un JSON válido EXACTAMENTE en el siguiente formato (sin texto adicional):\n"
            '{"questions": ["Pregunta 1", "Pregunta 2", ...]}\n'
            "Si no hay preguntas, devuelve: {\"questions\": []}."
        )
        response = ask_gpt(prompt_clarify)
    try:
        data = json.loads(response)
        questions = data.get("questions", [])
    except Exception as e:
        print(f"[activity_collector] Error al parsear preguntas: {e}")
        fallback_prompt = f"Genera en formato JSON una lista de preguntas de clarificación para el siguiente mensaje: '{last_msg}'. Usa el formato {{'questions': ['Pregunta 1', 'Pregunta 2', ...]}}."
        fallback_response = ask_gpt(fallback_prompt)
        try:
            data_fallback = json.loads(fallback_response)
            questions = data_fallback.get("questions", [])
        except Exception as e2:
            print(f"[activity_collector] Fallback error: {e2}")
            questions = ["¿Podrías darme más detalles sobre la actividad?"]
        item["clarification_questions"] = questions
        new_items.append(item)
        db.add_activity(user_id, item)
        print(f"[activity_collector] Actividad agregada: {item}")
    if new_items:
        llm_prompt = f"El mensaje '{last_msg}' generó las siguientes actividades: {new_items}. Explica por qué se detectaron estas actividades y qué elementos permitieron identificarlas."
    else:
        llm_prompt = f"El mensaje '{last_msg}' no generó actividades. Razona por qué no se detectaron actividades y qué elementos faltaron."
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
        "Determina la categoría de la actividad descrita basándote en el contexto y la intención. "
        "Devuelve **únicamente** un JSON válido EXACTAMENTE en el siguiente formato (sin texto adicional):\n"
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
    prompt = (
        f"Analiza el siguiente mensaje: '{msg}'. "
        "Extrae únicamente la parte que describe la actividad principal realizada por el usuario, "
        "ignorando cualquier pregunta o comentario que no describa una acción concreta. "
        "Devuelve **únicamente** un JSON válido EXACTAMENTE en el siguiente formato (sin texto adicional):\n"
        '{"activities": [{"title": "Descripción de la actividad", "category": "Categoría sugerida", "time_context": "past"}]}\n'
        "Si no se puede extraer una actividad clara, devuelve: {\"activities\": []}."
    )
    r = ask_gpt(prompt)
    if not r:
        return []
    r = r.replace("`json", "").replace("`", "").strip()
    try:
        data = json.loads(r)
        return data.get("activities", [])
    except Exception as e:
        print(f"[extract_sub_activities] Error: {e}")
        return []
