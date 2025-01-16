# /config/settings.py

import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Nuevo: token del bot de Discord
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")