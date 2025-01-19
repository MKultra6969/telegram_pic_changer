import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# API & Tokens
API_ID = int(os.getenv("API_ID", 0))  # Значение по умолчанию 0
API_HASH = os.getenv("API_HASH", "0")  # Значение по умолчанию "0"
BOT_TOKEN = os.getenv("BOT_TOKEN", "0")  # Значение по умолчанию "0"
ADMIN_ID = int(os.getenv("ADMIN_ID", 1745935544))  # Значение по умолчанию 1745935544

# Directories
SAVE_DIR = os.getenv("SAVE_DIR", "pictures")  # Значение по умолчанию "pictures"
LOG_DIR = os.getenv("LOG_DIR", "logs")  # Значение по умолчанию "logs"

# Logging
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILENAME = os.path.join(LOG_DIR, f'KAKASHKI-{current_time}.log')  # Можно изменить имя файла логов

# Pyrogram sessions
BOT_SESSION_NAME = os.getenv("BOT_SESSION_NAME", "Bot")  # Значение по умолчанию "Bot"
USER_SESSION_NAME = os.getenv("USER_SESSION_NAME", "User")  # Значение по умолчанию "User"

# Made by MKultra69, with love

# Саня, ты педик