[🇷🇺Русский](https://github.com/MKultra6969/telegram_pic_changer/blob/main/README.ru.md)

# **Profile Pic Changer Bot**

## **Description**

This **bot** is your solution for changing profile pictures in **Telegram**. Just send a photo to the bot — and voilà, you’ve got a new profile pic. It also includes features like **spam protection**, **timeouts**, and **user bans/unbans**, so no one messes around. Built on **Pyrogram**, which means it’s fast and reliable.

## **Features**

- **Profile Picture Change**: Send a photo — it updates your profile pic. Simple as that. 📸
- **Timeouts**: Don’t want to deal with constant profile pic changes? Set timeouts. ⏱
- **Spam Protection**: If spam gets out of hand, block profile picture changes for everyone. 🛑
- **User Bans**: Got some annoying troll spamming porn or trash? Ban them, and they’re done! 🚫
- **Commands**: Manage all this directly through Telegram. 🧑‍💻

## **Setup with Docker**

1. **Clone the repository**:
    ```bash
    git clone https://github.com/MKultra6969/telegram_pic_changer
    cd telegram_pic_changer
    ```

2. **Create a `.env` file**:
    In the project root, create a `.env` file or use the provided `env.env` template:
    ```env
    API_ID=your_api_id # Your API_ID
    API_HASH=your_api_hash # Your API_HASH
    BOT_TOKEN=your_bot_token # Your BOT_TOKEN
    ADMIN_ID=1745935544 # ADMIN_ID - by default, it's my ID
    SAVE_DIR=pictures # You can set any directory name for saving pictures
    LOG_DIR=logs # Any directory name for logs
    BOT_SESSION_NAME=Bot # Pyrogram session name for the bot
    USER_SESSION_NAME=User # Pyrogram session name for the user
    ```
    Get your credentials here:
    - **API_ID** and **API_HASH** — from [my.telegram.org](https://my.telegram.org/auth).
    - **BOT_TOKEN** — from [BotFather](https://core.telegram.org/bots#botfather).
    - **ADMIN_ID** — just your Telegram account ID.

3. **Build the Docker image**:
    ```bash
    docker build -t telegram-pic-changer .
    ```

4. **First run in interactive mode**:
    Pyrogram requires phone number verification, SMS code, and password (if 2FA is enabled). Run the container in interactive mode:
    ```bash
    docker run -it --rm --env-file .env telegram-pic-changer
    ```
    After successful authorization, the container will stop. You can now run it in detached mode.

5. **Run in detached mode**:
    ```bash
    docker run -d --env-file .env telegram-pic-changer
    ```

## **Commands**

- **/start** — Start the bot, and log when someone triggers it. 💬
- **/timeout <time>** — Set a global timeout for profile pic changes (e.g., `/timeout 1h`). ⏳
- **/timeout_user @username <time>** — Set a timeout for a specific user. ⏳
- **/stop_spam** — Disable profile pic changes for everyone. 🔒
- **/start_spam** — Enable profile pic changes for everyone. 🔓
- **/ban_user @username** — Ban a user from changing profile pics. 🚫
- **/unban_user @username** — Unban a user, allowing them to change profile pics. 🔓
- **/logs** — Retrieve logs via inline buttons. 📄
- **/images** — Send a ZIP archive of all saved profile pictures. 📦
- **/help** — Display a list of all admin commands. ℹ️

## **Notes**

- All user-uploaded photos are saved in the directory specified by **`SAVE_DIR=`**. 🗂
- Logs are stored in the directory specified by **`LOG_DIR=`**. 📑
- You can adjust directory names in **config.py** (if running directly via Python) or set parameters as described in step 2.
- During the **first run**, you MUST log in to your Telegram account.

## **License**

This creation is by MKultra69. In short, I don’t give a fuck about you. If it doesn’t work — maybe I’ll fix it later. But hey, give me credit if you use it — it’d be nice!


```bash
# +═════════════════════════════════════════════════════════════════════════+
# ║      ███▄ ▄███▓ ██ ▄█▀ █    ██  ██▓    ▄▄▄█████▓ ██▀███   ▄▄▄           ║
# ║     ▓██▒▀█▀ ██▒ ██▄█▒  ██  ▓██▒▓██▒    ▓  ██▒ ▓▒▓██ ▒ ██▒▒████▄         ║
# ║     ▓██    ▓██░▓███▄░ ▓██  ▒██░▒██░    ▒ ▓██░ ▒░▓██ ░▄█ ▒▒██  ▀█▄       ║
# ║     ▒██    ▒██ ▓██ █▄ ▓▓█  ░██░▒██░    ░ ▓██▓ ░ ▒██▀▀█▄  ░██▄▄▄▄██      ║
# ║     ▒██▒   ░██▒▒██▒ █▄▒▒█████▓ ░██████▒  ▒██▒ ░ ░██▓ ▒██▒ ▓█   ▓██▒     ║
# ║     ░ ▒░   ░  ░▒ ▒▒ ▓▒░▒▓▒ ▒ ▒ ░ ▒░▓  ░  ▒ ░░   ░ ▒▓ ░▒▓░ ▒▒   ▓▒█░     ║
# ║     ░  ░      ░░ ░▒ ▒░░░▒░ ░ ░ ░ ░ ▒  ░    ░      ░▒ ░ ▒░  ▒   ▒▒ ░     ║
# ║     ░      ░   ░ ░░ ░  ░░░ ░ ░   ░ ░     ░        ░░   ░   ░   ▒        ║
# ║            ░   ░  ░      ░         ░  ░            ░           ░  ░     ║
# ║                                  by                                     ║
# +═════════════════════════════════════════════════════════════════════════+

```
