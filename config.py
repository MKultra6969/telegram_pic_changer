# config.py

import os
from datetime import datetime

# API & Tokens
API_ID = 0 # pick it on https://my.telegram.org/auth
API_HASH = "Your Hash" # Pick it on https://my.telegram.org/auth
BOT_TOKEN = "YOUR TOKEN" # Pick it in bot father
ADMIN_ID = 1745935544  # ID of your TG account for admin permissions in bot

# Directories
SAVE_DIR = "avatars" # Change if needed
LOG_DIR = "logs" # Change if needed

# Logging
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILENAME = os.path.join(LOG_DIR, f'avatar_bot-{current_time}.log') # You can also change the name of the log file by changing 'avatar_bot'

# Pyrogram sessions
BOT_SESSION_NAME = "avatar_bot" # Change name if needed
USER_SESSION_NAME = "my_account" # Change name if needed


# Made by MKultra69, with love

# Саня, ты педик
