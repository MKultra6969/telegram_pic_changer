import logging
import os
import time
import json
from moviepy.video.io.VideoFileClip import VideoFileClip
from PIL import Image
from pyrogram import Client, filters
from datetime import timedelta
from config import API_ID, API_HASH, BOT_TOKEN, ADMIN_ID, SAVE_DIR, LOG_DIR, LOG_FILENAME, BOT_SESSION_NAME, USER_SESSION_NAME

BAN_LIST_FILE = "ban_list.json"

# Создаем папку для логов, если она не существует
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,  # Уровень INFO для важной информации
    format="%(asctime)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILENAME),  # Запись в файл с датой и временем
        logging.StreamHandler()  # Также выводим в консоль
    ]
)

# Устанавливаем уровень логирования для Pyrogram
logging.getLogger("pyrogram").setLevel(logging.WARNING)  # Только WARNING и выше для Pyrogram


def load_ban_list():
    """Загружает список забаненных пользователей из файла."""
    if os.path.exists(BAN_LIST_FILE):
        try:
            with open(BAN_LIST_FILE, "r", encoding="utf-8") as file:
                banned_users = set(json.load(file))
                logging.info(f"Список забаненных пользователей загружен, найдено {len(banned_users)} пользователей.")
                return banned_users
        except json.JSONDecodeError:
            logging.error("Ошибка при загрузке списка забаненных пользователей: файл поврежден.")
            return set()
        except Exception as e:
            logging.error(f"Неизвестная ошибка при загрузке списка забаненных пользователей: {e}")
            return set()
    else:
        logging.info(f"Файл {BAN_LIST_FILE} не найден, создается пустой список забаненных.")
        return set()


def save_ban_list():
    """Сохраняет список забаненных пользователей в файл."""
    try:
        with open(BAN_LIST_FILE, "w", encoding="utf-8") as file:
            json.dump(list(banned_users), file, ensure_ascii=False, indent=4)
            logging.info("Список забаненных пользователей сохранен.")
    except Exception as e:
        logging.error(f"Ошибка при сохранении списка забаненных пользователей: {e}")


# Загружаем список забаненных пользователей при запуске
banned_users = load_ban_list()

# Создаем папку для сохранения аватарок, если она не существует
os.makedirs(SAVE_DIR, exist_ok=True)

# bot client
bot = Client(BOT_SESSION_NAME, api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# user client
user_client = Client(USER_SESSION_NAME, api_id=API_ID, api_hash=API_HASH)

# Структуры для хранения информации о тайм-аутах и блокировках
user_timeouts = {}
global_timeout = None  # Глобальный тайм-аут
spam_blocked = False
banned_users = set()  # Множество забаненных пользователей


def get_next_filename():
    """Определяет имя следующего файла с аватаркой."""
    existing_files = [f for f in os.listdir(SAVE_DIR) if f.startswith("pic") and f.endswith(".jpg")]
    nums = [
        int(f.replace("pic", "").replace(".jpg", ""))
        for f in existing_files if f[3:-4].isdigit()
    ]
    next_num = max(nums, default=0) + 1
    return os.path.join(SAVE_DIR, f"pic{next_num}.jpg")


def parse_timeout(timeout_str):
    """Парсит строку с тайм-аутом в формат timedelta."""
    if timeout_str.endswith('s'):
        return timedelta(seconds=int(timeout_str[:-1]))  # Поддержка секунд
    elif timeout_str.endswith('m'):
        return timedelta(minutes=int(timeout_str[:-1]))
    elif timeout_str.endswith('h'):
        return timedelta(hours=int(timeout_str[:-1]))
    elif timeout_str.endswith('d'):
        return timedelta(days=int(timeout_str[:-1]))
    return None

def process_video(file_path):
    """Обрабатывает видео или GIF, чтобы оно соответствовало требованиям Telegram."""
    try:
        video = VideoFileClip(file_path)

        # Ограничиваем длительность
        if video.duration > 10:
            video = video.subclipped(0, 10)

        # Ограничиваем разрешение
        video = video.resize(height=640, width=640)  # Указываем только высоту для сохранения пропорций.

        # Убираем звук
        output_path = file_path.replace(".mp4", "_processed.mp4")
        video.write_videofile(output_path, codec="libx264", audio=False)

        return output_path
    except Exception as e:
        logging.error(f"Ошибка при обработке видео: {e}")
        return None
    finally:
        video.close()  # Закрываем объект VideoFileClip


@bot.on_message(filters.private & (filters.photo | filters.video | filters.animation))
async def handle_media(client, message):
    user_id = message.from_user.id
    username = message.from_user.username or "без имени"

    # Проверяем, заблокирован ли доступ
    if spam_blocked:
        await message.reply("Доступ на смену аватарки закрыт, иди нахуй.")
        logging.warning(f"Попытка смены аватарки от @{username} (ID: {user_id}), доступ заблокирован.")
        return

    # Проверяем, если пользователь забанен
    if user_id in banned_users:
        await message.reply("ТЫ ЗАБАНЕН, УЕБИЩЕ")
        logging.warning(f"Попытка смены аватарки от @{username} (ID: {user_id}), пользователь забанен.")
        return

    # Проверяем, если установлен тайм-аут для этого пользователя
    current_time = time.time()
    last_time = user_timeouts.get(user_id, 0)

    # Проверяем глобальный тайм-аут
    if global_timeout and (current_time - last_time) < global_timeout.total_seconds():
        wait_time = global_timeout.total_seconds() - (current_time - last_time)
        await message.reply(f"Жди {int(wait_time // 60)} минут до следующей смены аватарки.")
        logging.info(f"Попытка смены аватарки от @{username} (ID: {user_id}), тайм-аут не прошел.")
        return

    # Определяем, какой тип медиа был отправлен
    file_path = get_next_filename()

    if message.photo:
        file_id = message.photo.file_id
        await bot.download_media(file_id, file_name=file_path)
    elif message.video:
        file_id = message.video.file_id
        await bot.download_media(file_id, file_name=file_path)
        file_path = process_video(file_path)
        if not file_path:
            await message.reply("Не удалось обработать видео.")
            return
    elif message.animation:
        file_id = message.animation.file_id
        await bot.download_media(file_id, file_name=file_path)
        file_path = process_video(file_path)
        if not file_path:
            await message.reply("Не удалось обработать GIF.")
            return
    else:
        await message.reply("Тип медиа не поддерживается для смены аватарки.")
        return

    logging.info(f"Медиа сохранено: {file_path}")

    # Меняем аватарку
    try:
        await user_client.set_profile_photo(photo=file_path)
        user_timeouts[user_id] = current_time  # Обновление времени последнего запроса
        await message.reply("ГОТОВО, ПРОВЕРЯЙ")
        logging.info(f"Аватарка успешно обновлена для @{username} (ID: {user_id})")
    except Exception as e:
        logging.error(f"Ошибка при смене аватарки для @{username} (ID: {user_id}): {e}")
        await message.reply(f"ТЫ ДОЛБАЕБ? НИЧЕ НЕ ПОЛУЧИТСЯ, ПОКА. {e}")


@bot.on_message(filters.command("start"))
async def start_message(client, message):
    welcome_text = (
        "ОТПРАВЬ МНЕ ЛЮБУЮ ЕБАНУЮ ФОТКУ, И Я СМЕНЮ ЕЕ В ПРОФИЛЕ @mkultra6969.\n\n"
        "Если не получится — ТО ВИНОВАТ ИСКЛЮЧИТЕЛЬНО ЮЗЕР НО НЕ РАЗРАБ.😋😋😋"
    )
    await message.reply(welcome_text)
    username = message.from_user.username or "без имени"
    logging.info(f"Юзер нажал START в боте @{username} id: {message.from_user.id}")



@bot.on_message(filters.command("timeout"))
async def set_timeout(client, message):
    global global_timeout
    if message.from_user.id != ADMIN_ID:
        await message.reply("Куда ты лезишь чючело ебаное.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Используй: /timeout <время>, например /timeout 1h.")
        return

    timeout_str = parts[1]
    timeout = parse_timeout(timeout_str)
    if timeout:
        global_timeout = timeout
        await message.reply(f"Тайм-аут для смены аватарки установлен на {timeout_str}.")
        logging.info(f"Тайм-аут для смены аватарки установлен на {timeout_str}.")
    else:
        await message.reply("Неизвестный формат времени. Используй s (секунды), m (минуты), h (часы), d (дни).")


@bot.on_message(filters.command("timeout_user"))
async def set_user_timeout(client, message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("ПОШЕЛ НАХУЙ, ГЛАВНЫЙ ТУТ MKultra.")
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.reply("Используй: /timeout_user @username 1h или /timeout_user <id> 1h.")
        return

    username_or_id = parts[1]
    timeout_str = parts[2]
    timeout = parse_timeout(timeout_str)

    if timeout:
        if username_or_id.startswith('@'):
            username = username_or_id[1:]
            user_id = await get_user_id_by_username(username)
            if user_id:
                user_timeouts[user_id] = time.time()  # Устанавливаем текущее время
                await message.reply(f"Тайм-аут для @{username} установлен на {timeout_str}.")
                logging.info(f"Тайм-аут для @{username} установлен на {timeout_str}.")
            else:
                await message.reply(f"Не удалось найти пользователя @{username}.")
        else:
            try:
                user_id = int(username_or_id)
                user_timeouts[user_id] = time.time()  # Устанавливаем текущее время
                await message.reply(f"Тайм-аут для пользователя {user_id} установлен на {timeout_str}.")
                logging.info(f"Тайм-аут для пользователя {user_id} установлен на {timeout_str}.")
            except ValueError:
                await message.reply("Некорректный ID пользователя.")
    else:
        await message.reply("Неизвестный формат времени.")


@bot.on_message(filters.command("stop_spam"))
async def stop_spam(client, message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("ПОШЕЛ НАХУЙ, ГЛАВНЫЙ ТУТ MKultra.")
        return

    global spam_blocked
    spam_blocked = True
    await message.reply("Сменить аватарку всем пользователям теперь нельзя.")
    logging.info("Доступ на смену аватарки заблокирован для всех.")


@bot.on_message(filters.command("start_spam"))
async def start_spam(client, message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("ПОШЕЛ НАХУЙ, ГЛАВНЫЙ ТУТ MKultra.")
        return

    global spam_blocked
    spam_blocked = False
    await message.reply("Сменить аватарку снова можно.")
    logging.info("Доступ на смену аватарки возобновлен для всех пользователей.")


@bot.on_message(filters.command("ban_user"))
async def ban_user(client, message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("ПОШЕЛ НАХУЙ, ГЛАВНЫЙ ТУТ MKultra.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Используй: /ban_user @username или /ban_user <id>.")
        return

    username_or_id = parts[1]
    if username_or_id.startswith('@'):
        username = username_or_id[1:]
        user_id = await get_user_id_by_username(username)
        if user_id:
            if user_id in banned_users:
                await message.reply(f"Пользователь @{username} уже забанен.")
                logging.info(f"Попытка забанить уже забаненного пользователя @{username}.")
            else:
                banned_users.add(user_id)
                save_ban_list()  # Сохраняем изменения
                await message.reply(f"Пользователь @{username} забанен.")
                logging.info(f"Пользователь @{username} забанен.")
        else:
            await message.reply(f"Не удалось найти пользователя @{username}.")
    else:
        try:
            user_id = int(username_or_id)
            if user_id in banned_users:
                await message.reply(f"Пользователь {user_id} уже забанен.")
                logging.info(f"Попытка забанить уже забаненного пользователя {user_id}.")
            else:
                banned_users.add(user_id)
                save_ban_list()  # Сохраняем изменения
                await message.reply(f"Пользователь {user_id} забанен.")
                logging.info(f"Пользователь {user_id} забанен.")
        except ValueError:
            await message.reply("Некорректный ID пользователя.")


@bot.on_message(filters.command("unban_user"))
async def unban_user(client, message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("ПОШЕЛ НАХУЙ, ГЛАВНЫЙ ТУТ MKultra.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Используй: /unban_user @username или /unban_user <id>.")
        return

    username_or_id = parts[1]
    if username_or_id.startswith('@'):
        username = username_or_id[1:]
        user_id = await get_user_id_by_username(username)
        if user_id:
            if user_id in banned_users:
                banned_users.remove(user_id)
                save_ban_list()  # Сохраняем изменения
                await message.reply(f"Пользователь @{username} разблокирован.")
                logging.info(f"Пользователь @{username} разблокирован.")
            else:
                await message.reply(f"Пользователь @{username} не был забанен.")
                logging.info(f"Попытка разбанить не забаненного пользователя @{username}.")
        else:
            await message.reply(f"Не удалось найти пользователя @{username}.")
    else:
        try:
            user_id = int(username_or_id)
            if user_id in banned_users:
                banned_users.remove(user_id)
                save_ban_list()  # Сохраняем изменения
                await message.reply(f"Пользователь {user_id} разблокирован.")
                logging.info(f"Пользователь {user_id} разблокирован.")
            else:
                await message.reply(f"Пользователь {user_id} не был забанен.")
                logging.info(f"Попытка разбанить не забаненного пользователя {user_id}.")
        except ValueError:
            await message.reply("Некорректный ID пользователя.")


async def get_user_id_by_username(username):
    try:
        user = await bot.get_users(username)
        return user.id
    except Exception as e:
        logging.error(f"Ошибка при получении ID пользователя {username}: {e}")
        return None


if __name__ == "__main__":
    try:
        logging.info("Запуск user клиента...")
        user_client.start()
        logging.info("Запуск бота...")
        bot.run()
    except Exception as e:
        logging.critical(f"Фатальная ошибка: {e}")
    finally:
        user_client.stop()
        logging.info("Сессия завершена")

# Sanya ti pedic
# Made by MKultra69
# GFY

# Какие то из комментов специально добавлены с помощью ИИ

# UPD 01/19/25 - я выкурил примерно 27 сигарет за все время написания этого говна
# UPD 01/19/25 10:05 - я выкурил уже, вероятно, более пачки...

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
