[🇷🇺Русский](https://github.com/MKultra6969/telegram_pic_changer/blob/main/README.ru.md)

# **Profile Pic Changer Bot**

## **Description**

This **bot** is your go-to solution for changing profile pictures in **Telegram**. Just send a photo to the bot — and boom, new profile pic. Also includes features like **spam protection**, **timeouts**, and **ban-unban** users so nobody fucks with you. Built with **Pyrogram**, meaning it's fast and smooth.

## **Features**

- **Profile Pic Change**: send a photo — bam, your pic's changed. Simple as that. 📸
- **Timeouts**: don't wanna get spammed with pics every 5 seconds? Set timeouts. ⏱
- **Spam Block**: if everyone is being a pain in the ass — block pic changes for everyone. 🛑
- **Ban Users**: got some asshole spamming porn or other trash? Ban him to hell and done. 🚫
- **Commands**: you control all this shit through Telegram. 🧑‍💻

## **Installation**

1. **Clone the repo**:
    ```bash
    git clone https://github.com/MKultra6969/telegram_pic_changer
    cd telegram_pic_changer
    ```

2. **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3. **Configure the bot**:
    - Get your **API_ID** and **API_HASH** from [my.telegram.org](https://my.telegram.org/auth).
    - Get your **BOT_TOKEN** from [BotFather](https://core.telegram.org/bots#botfather).
    - Put your **ADMIN_ID** (just your Telegram account ID) for admin commands.

4. **Run the bot**:
    ```bash
    python bot.py
    ```

## **Commands**

- **/start** — Starts the bot and logs when someone hits it. 💬
- **/timeout <time>** — Global timeout for profile pic changes (e.g., `/timeout 1h`). ⏳
- **/timeout_user @username <time>** — Timeout for a specific user. ⏳
- **/stop_spam** — Block profile pic changes for everyone. 🔒
- **/start_spam** — Open profile pic changes for everyone. 🔓
- **/ban_user @username** — Ban a user, stop them from changing their pic. 🚫
- **/unban_user @username** — Unban a user, they can change their pic again. 🔓

## **Notes**

- All the photos users send are saved in the **avatars** folder. 🗂
- Logs are saved in the **logs** folder. 📑
- You can also change names through **config.py**.

## **License**

This creation is by MKultra69, so as usual, I don't give a shit if it doesn't work — maybe I'll fix it someday. But seriously, if you're using it, at least mention me, it’ll make me happy!
