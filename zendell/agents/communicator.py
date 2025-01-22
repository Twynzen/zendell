# agents/communicator.py

import asyncio
from datetime import datetime
from typing import Optional

from zendell.services.discord_service import send_dm
from zendell.core.db import MongoDBManager
from zendell.agents.goal_finder import goal_finder_node
from zendell.agents.activity_collector import activity_collector_node
from zendell.services.llm_provider import ask_gpt
from zendell.agents.conversation_analyzer import analyze_conversation_flow
import json

def extract_user_name_via_llm(user_text: str) -> Optional[str]:
    prompt = f"""
Analiza este texto de un usuario: "{user_text}"
1) Determina si el usuario ha mencionado su nombre, y si es así, cuál es.
2) Responde en JSON con "found_name" (true/false) y "name" (string).
   Si no hay nombre, "found_name": false, "name": "".
"""
    response = ask_gpt(prompt)
    try:
        data = json.loads(response)
        if data.get("found_name") is True and data.get("name"):
            return data["name"]
    except:
        pass
    return None

class Communicator:
    def __init__(self, db_manager: MongoDBManager):
        self.db_manager = db_manager
        self.conversations = {}  # {discord_user_id: [mensaje1, mensaje2, ...]}

    async def on_user_message(self, message_text: str, author_id: str):
        print(f"[Communicator] Mensaje recibido de user_id={author_id}: {message_text}")

        # 1. Obtenemos el estado actual
        current_state = self.db_manager.get_state(author_id)

        # 2. Chequeamos si el usuario se presentó (vía LLM)
        maybe_name = extract_user_name_via_llm(message_text)
        if maybe_name:
            print(f"[Communicator] Detectamos que el usuario se llama: {maybe_name}")
            current_state["customer_name"] = maybe_name
            self.db_manager.save_state(author_id, current_state)

        # 3. Determinamos speaker_name para la BD
        speaker_name = current_state.get("customer_name", "")
        if not speaker_name:
            speaker_name = f"User_{author_id[-4:]}"  # fallback si no hay nombre

        # 4. Logueamos el mensaje del usuario
        self.db_manager.log_message(
            user_id=author_id,
            message=message_text,
            is_bot=False,
            speaker_name=speaker_name, 
            agent_name="communicator"
        )

        # 5. Podrías llamar activity_collector_node si gustas
        updated_state = activity_collector_node(state=current_state, new_activity=message_text)
        self.db_manager.save_state(author_id, updated_state)

        # 6. Macro-análisis
        analysis_result = analyze_conversation_flow(self.db_manager, author_id, limit=30)
        overall_mood = analysis_result.get("overall_mood", "neutral")
        wants_to_stop = analysis_result.get("wants_to_stop", False)

        # 7. Si LLM dice que el user quiere parar
        if wants_to_stop:
            goodbye = "Entiendo que prefieres descansar ahora. ¡Ánimo, hablamos luego!"
            await send_dm(author_id, goodbye)
            self.db_manager.log_message(
                user_id=author_id,
                message=goodbye,
                is_bot=True,
                speaker_name="Zendell",
                agent_name="communicator"
            )
            self.conversations.pop(author_id, None)
            return

        # 8. Generamos respuesta del LLM (basado en summary)
        summary = analysis_result.get("summary", "")
        followup_prompt = f"""Eres un sistema conversando con el usuario.
La conversación completa se resume así: {summary}.
El estado emocional global es {overall_mood}.
Sigue la charla de forma empática. 
No finalices a menos que sea evidente que el usuario desea parar.
Habla como un amigo cercano, en tono natural."""
        followup_response = ask_gpt(followup_prompt)

        # 9. Enviamos la respuesta y la guardamos en DB
        await send_dm(author_id, followup_response)
        self.db_manager.log_message(
            user_id=author_id,
            message=followup_response,
            is_bot=True,
            speaker_name="Zendell",
            agent_name="communicator"
        )

    async def trigger_interaction(self, _user_id: str):
        print("[Communicator] Iniciando interacción (sin depender de user_id).")
        goal_state = goal_finder_node("", self.db_manager)
        # Lógica para primer mensaje
        if not goal_state.get("general_info"):
            message = "¡Hola! La base de datos no responde, pero te saludo en modo temporal."
        elif "respuesta_inicial" in goal_state["general_info"]:
            message = goal_state["general_info"]["respuesta_inicial"]
        else:
            short_term_info = goal_state.get("short_term_info", [])
            message = short_term_info[-1] if short_term_info else "¡Hola, algo salió raro!"

        # Mandamos el primer msj
        await send_dm("", message)
        # Log de bot
        self.db_manager.log_message(
            user_id=_user_id,
            message=message,
            is_bot=True,
            speaker_name="Zendell",
            agent_name="communicator"
        )
