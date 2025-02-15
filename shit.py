import logging
import os
import time
import json
from moviepy.video.io.VideoFileClip import VideoFileClip
from PIL import Image
from pyrogram import Client, filters
from datetime import timedelta
from config import API_ID, API_HASH, BOT_TOKEN, ADMIN_ID, SAVE_DIR, LOG_DIR, LOG_FILENAME, BOT_SESSION_NAME, USER_SESSION_NAME
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import zipfile
import datetime

BAN_LIST_FILE = "ban_list.json"

# Создаем папку для логов, если она не существует
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Настройка логирования:
# - Выводится время, уровень логирования, имя файла, функция и сообщение.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILENAME),
        logging.StreamHandler()
    ]
)

# Для Pyrogram выводим только WARNING и выше (чтобы не захламлять логи)
logging.getLogger("pyrogram").setLevel(logging.WARNING)


def load_ban_list():
    """
    Загружает список забаненных пользователей из файла.
    Если файл существует и содержит корректный JSON, возвращает множество ID пользователей.
    В противном случае возвращает пустое множество.
    """
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
    """
    Сохраняет список забаненных пользователей в файл.
    Использует глобальную переменную banned_users.
    """
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

# Создаем клиенты Pyrogram: один для бота, другой для смены аватарки (user_client)
bot = Client(BOT_SESSION_NAME, api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user_client = Client(USER_SESSION_NAME, api_id=API_ID, api_hash=API_HASH)

# Структуры для хранения данных:
user_timeouts = {}     # Словарь: {user_id: время последней смены аватарки}
global_timeout = None  # Глобальный тайм-аут, устанавливаемый админом
spam_blocked = False   # Флаг, блокирующий смену аватарки для всех пользователей

# Примечание: banned_users уже загружен выше, поэтому не переопределяем его!


def get_next_filename():
    """
    Определяет имя следующего файла для сохранения аватарки.
    Ищет файлы с префиксом "pic" и расширением ".jpg" в SAVE_DIR,
    затем определяет максимальный номер и увеличивает его на 1.
    """
    existing_files = [f for f in os.listdir(SAVE_DIR) if f.startswith("pic") and f.endswith(".jpg")]
    nums = [int(f.replace("pic", "").replace(".jpg", "")) for f in existing_files if f[3:-4].isdigit()]
    next_num = max(nums, default=0) + 1
    return os.path.join(SAVE_DIR, f"pic{next_num}.jpg")


def parse_timeout(timeout_str):
    """
    Парсит строку тайм-аута и возвращает объект timedelta.
    Поддерживаются секунды (s), минуты (m), часы (h) и дни (d).
    """
    if timeout_str.endswith('s'):
        return timedelta(seconds=int(timeout_str[:-1]))
    elif timeout_str.endswith('m'):
        return timedelta(minutes=int(timeout_str[:-1]))
    elif timeout_str.endswith('h'):
        return timedelta(hours=int(timeout_str[:-1]))
    elif timeout_str.endswith('d'):
        return timedelta(days=int(timeout_str[:-1]))
    return None


def process_video(file_path):
    """
    Обрабатывает видео или GIF для соответствия требованиям Telegram:
    - Ограничивает длительность до 10 секунд.
    - Меняет разрешение на 640x640 (с сохранением пропорций).
    - Убирает звук.
    Возвращает путь к обработанному файлу или None в случае ошибки.
    """
    try:
        video = VideoFileClip(file_path)
        # Ограничиваем длительность до 10 секунд, если нужно
        if video.duration > 10:
            video = video.subclip(0, 10)
        # Изменяем разрешение
        video = video.resize(height=640, width=640)
        # Убираем звук и сохраняем обработанное видео
        output_path = file_path.replace(".mp4", "_processed.mp4")
        video.write_videofile(output_path, codec="libx264", audio=False)
        logging.info(f"Видео обработано и сохранено: {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"Ошибка при обработке видео: {e}")
        return None
    finally:
        video.close()


@bot.on_message(filters.private & (filters.photo | filters.video | filters.animation))
async def handle_media(client, message):
    """
    Обрабатывает входящие медиа-сообщения:
    - Проверяет, не заблокирован ли доступ и не установлен ли тайм-аут.
    - Скачивает медиа-файл.
    - Если это видео или GIF, обрабатывает его.
    - Меняет аватарку через user_client.
    """
    user_id = message.from_user.id
    username = message.from_user.username or "без имени"

    # Проверка блокировки смены аватарки для всех
    if spam_blocked:
        await message.reply("Доступ на смену аватарки закрыт, иди нахуй.")
        logging.warning(f"Попытка смены аватарки от @{username} (ID: {user_id}) при блокировке.")
        return

    # Проверка: если пользователь забанен
    if user_id in banned_users:
        await message.reply("ТЫ ЗАБАНЕН, УЕБИЩЕ")
        logging.warning(f"Попытка смены аватарки от забаненного пользователя @{username} (ID: {user_id}).")
        return

    # Проверка тайм-аута для конкретного пользователя
    current_time = time.time()
    last_time = user_timeouts.get(user_id, 0)
    if global_timeout and (current_time - last_time) < global_timeout.total_seconds():
        wait_time = global_timeout.total_seconds() - (current_time - last_time)
        await message.reply(f"Жди {int(wait_time // 60)} минут до следующей смены аватарки.")
        logging.info(f"Тайм-аут не прошел для @{username} (ID: {user_id}). Осталось ждать {wait_time} секунд.")
        return

    # Скачиваем медиа-файл
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

    # Меняем аватарку через user_client
    try:
        await user_client.set_profile_photo(photo=file_path)
        user_timeouts[user_id] = current_time  # Обновляем время последнего запроса
        await message.reply("ГОТОВО, ПРОВЕРЯЙ")
        logging.info(f"Аватарка успешно обновлена для @{username} (ID: {user_id}).")
    except Exception as e:
        logging.error(f"Ошибка при смене аватарки для @{username} (ID: {user_id}): {e}")
        await message.reply(f"ТЫ ДОЛБАЕБ? НИЧЕ НЕ ПОЛУЧИТСЯ, ПОКА. {e}")


@bot.on_message(filters.command("start"))
async def start_message(client, message):
    """
    Команда /start отправляет приветственное сообщение с инструкциями.
    """
    welcome_text = (
        "ОТПРАВЬ МНЕ ЛЮБУЮ ЕБАНУЮ ФОТКУ, И Я СМЕНЮ ЕЕ В ПРОФИЛЕ @mkultra6969.\n\n"
        "Если не получится — ТО ВИНОВАТ ИСКЛЮЧИТЕЛЬНО ЮЗЕР НО НЕ РАЗРАБ.😋😋😋"
    )
    await message.reply(welcome_text)
    username = message.from_user.username or "без имени"
    logging.info(f"/start вызван пользователем @{username} (ID: {message.from_user.id}).")


@bot.on_message(filters.command("timeout"))
async def set_timeout(client, message):
    """
    Команда /timeout <время> устанавливает глобальный тайм-аут для смены аватарки.
    Пример: /timeout 1h
    Доступна только для админа.
    """
    global global_timeout
    if message.from_user.id != ADMIN_ID:
        await message.reply("Куда ты лезешь чючело ебаное.")
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
        logging.info(f"Глобальный тайм-аут {timeout_str} установлен админом {message.from_user.id}.")
    else:
        await message.reply("Неизвестный формат времени. Используй s, m, h или d.")


@bot.on_message(filters.command("timeout_user"))
async def set_user_timeout(client, message):
    """
    Команда /timeout_user <@username или id> <время> устанавливает тайм-аут для конкретного пользователя.
    Пример: /timeout_user @username 1h
    Доступна только для админа.
    """
    if message.from_user.id != ADMIN_ID:
        await message.reply("ПОШЕЛ НАХУЙ, ГЛАВНЫЙ ТУТ MKultra.")
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.reply("Используй: /timeout_user <@username или id> <время> (например, /timeout_user @username 1h).")
        return

    username_or_id = parts[1]
    timeout_str = parts[2]
    timeout = parse_timeout(timeout_str)

    if timeout:
        if username_or_id.startswith('@'):
            username = username_or_id[1:]
            user_id = await get_user_id_by_username(username)
            if user_id:
                user_timeouts[user_id] = time.time()
                await message.reply(f"Тайм-аут для @{username} установлен на {timeout_str}.")
                logging.info(f"Тайм-аут для @{username} ({user_id}) установлен на {timeout_str} админом {message.from_user.id}.")
            else:
                await message.reply(f"Не удалось найти пользователя @{username}.")
                logging.error(f"Пользователь @{username} не найден для установки тайм-аута.")
        else:
            try:
                user_id = int(username_or_id)
                user_timeouts[user_id] = time.time()
                await message.reply(f"Тайм-аут для пользователя {user_id} установлен на {timeout_str}.")
                logging.info(f"Тайм-аут для пользователя {user_id} установлен на {timeout_str} админом {message.from_user.id}.")
            except ValueError:
                await message.reply("Некорректный ID пользователя.")
                logging.error(f"Некорректный ID в команде /timeout_user: {username_or_id}")
    else:
        await message.reply("Неизвестный формат времени.")


@bot.on_message(filters.command("stop_spam"))
async def stop_spam(client, message):
    """
    Команда /stop_spam блокирует возможность смены аватарки для всех пользователей.
    Доступна только для админа.
    """
    if message.from_user.id != ADMIN_ID:
        await message.reply("ПОШЕЛ НАХУЙ, ГЛАВНЫЙ ТУТ MKultra.")
        return

    global spam_blocked
    spam_blocked = True
    await message.reply("Сменить аватарку всем пользователям теперь нельзя.")
    logging.info("Доступ на смену аватарки заблокирован админом.")


@bot.on_message(filters.command("start_spam"))
async def start_spam(client, message):
    """
    Команда /start_spam снимает блокировку смены аватарки для всех пользователей.
    Доступна только для админа.
    """
    if message.from_user.id != ADMIN_ID:
        await message.reply("ПОШЕЛ НАХУЙ, ГЛАВНЫЙ ТУТ MKultra.")
        return

    global spam_blocked
    spam_blocked = False
    await message.reply("Сменить аватарку снова можно.")
    logging.info("Доступ на смену аватарки возобновлен админом.")


@bot.on_message(filters.command("ban_user"))
async def ban_user(client, message):
    """
    Команда /ban_user <@username или id> блокирует возможность смены аватарки для указанного пользователя.
    Доступна только для админа.
    """
    if message.from_user.id != ADMIN_ID:
        await message.reply("ПОШЕЛ НАХУЙ, ГЛАВНЫЙ ТУТ MKultra.")
        logging.warning(f"Попытка /ban_user от неадмина {message.from_user.id}.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Используй: /ban_user <@username или id>.")
        logging.info("Неверное использование команды /ban_user.")
        return

    username_or_id = parts[1]
    if username_or_id.startswith('@'):
        username = username_or_id[1:]
        user_id = await get_user_id_by_username(username)
        if user_id:
            if user_id in banned_users:
                await message.reply(f"Пользователь @{username} уже забанен.")
                logging.info(f"Повторный бан @{username}.")
            else:
                banned_users.add(user_id)
                save_ban_list()
                await message.reply(f"Пользователь @{username} забанен.")
                logging.info(f"Пользователь @{username} (ID: {user_id}) забанен админом {message.from_user.id}.")
        else:
            await message.reply(f"Не удалось найти пользователя @{username}.")
            logging.error(f"Пользователь @{username} не найден для бана.")
    else:
        try:
            user_id = int(username_or_id)
            if user_id in banned_users:
                await message.reply(f"Пользователь {user_id} уже забанен.")
                logging.info(f"Повторный бан пользователя {user_id}.")
            else:
                banned_users.add(user_id)
                save_ban_list()
                await message.reply(f"Пользователь {user_id} забанен.")
                logging.info(f"Пользователь {user_id} забанен админом {message.from_user.id}.")
        except ValueError:
            await message.reply("Некорректный ID пользователя.")
            logging.error(f"Некорректный ID в команде /ban_user: {username_or_id}")


@bot.on_message(filters.command("unban_user"))
async def unban_user(client, message):
    """
    Команда /unban_user <@username или id> разблокирует возможность смены аватарки для указанного пользователя.
    Доступна только для админа.
    """
    if message.from_user.id != ADMIN_ID:
        await message.reply("ПОШЕЛ НАХУЙ, ГЛАВНЫЙ ТУТ MKultra.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Используй: /unban_user <@username или id>.")
        return

    username_or_id = parts[1]
    if username_or_id.startswith('@'):
        username = username_or_id[1:]
        user_id = await get_user_id_by_username(username)
        if user_id:
            if user_id in banned_users:
                banned_users.remove(user_id)
                save_ban_list()
                await message.reply(f"Пользователь @{username} разблокирован.")
                logging.info(f"Пользователь @{username} разблокирован админом {message.from_user.id}.")
            else:
                await message.reply(f"Пользователь @{username} не был забанен.")
                logging.info(f"Попытка разбанить незабаненного @{username}.")
        else:
            await message.reply(f"Не удалось найти пользователя @{username}.")
    else:
        try:
            user_id = int(username_or_id)
            if user_id in banned_users:
                banned_users.remove(user_id)
                save_ban_list()
                await message.reply(f"Пользователь {user_id} разблокирован.")
                logging.info(f"Пользователь {user_id} разблокирован админом {message.from_user.id}.")
            else:
                await message.reply(f"Пользователь {user_id} не был забанен.")
                logging.info(f"Попытка разбанить незабаненного пользователя {user_id}.")
        except ValueError:
            await message.reply("Некорректный ID пользователя.")


async def get_user_id_by_username(username):
    """
    Асинхронная функция для получения ID пользователя по его username.
    В случае ошибки логирует её и возвращает None.
    """
    try:
        user = await bot.get_users(username)
        return user.id
    except Exception as e:
        logging.error(f"Ошибка при получении ID пользователя {username}: {e}")
        return None


@bot.on_message(filters.command("logs"))
async def logs_menu(client, message):
    """
    Команда /logs выводит список файлов логов через инлайн-клавиатуру.
    Доступна только для админа.
    """
    if message.from_user.id != ADMIN_ID:
        await message.reply("Пошёл на хуй, главный тут MKultra.")
        return

    # Получаем список логов из папки LOG_DIR
    log_files = [f for f in os.listdir(LOG_DIR) if f.endswith('.log')]
    if not log_files:
        await message.reply("Логов нет, иди нахуй.")
        return

    # Формируем инлайн-кнопки для каждого файла
    buttons = [[InlineKeyboardButton(text=log, callback_data=f"log_{log}")] for log in log_files]
    markup = InlineKeyboardMarkup(buttons)
    await message.reply("Выбери лог для выгрузки:", reply_markup=markup)
    logging.info(f"Пользователь {message.from_user.id} запросил выгрузку логов.")


@bot.on_callback_query(filters.regex(r"^log_"))
async def send_log_file(client, callback_query):
    """
    Обрабатывает нажатие на кнопку лог файла и отправляет файл,
    если он существует, либо выводит ошибку.
    """
    log_filename = callback_query.data.split("log_", 1)[1]
    file_path = os.path.join(LOG_DIR, log_filename)
    if os.path.exists(file_path):
        await callback_query.message.reply_document(file_path)
        await callback_query.answer()
        logging.info(f"Отправлен лог файл: {log_filename}")
    else:
        await callback_query.answer("Лог не найден", show_alert=True)
        logging.error(f"Лог файл не найден: {log_filename}")


@bot.on_message(filters.command("images"))
async def send_images_archive(client, message):
    """
    Команда /images архивирует все jpg-файлы из SAVE_DIR, отправляет архив,
    а затем удаляет временный архив.
    Доступна только для админа.
    """
    if message.from_user.id != ADMIN_ID:
        await message.reply("Пошёл на хуй, главный тут MKultra.")
        return

    archive_name = f"images_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.zip"
    archive_path = os.path.join(SAVE_DIR, archive_name)

    try:
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for file in os.listdir(SAVE_DIR):
                if file.endswith('.jpg'):
                    full_path = os.path.join(SAVE_DIR, file)
                    archive.write(full_path, arcname=file)
        await message.reply_document(archive_path)
        logging.info(f"Архив с изображениями отправлен: {archive_name}")
    except Exception as e:
        logging.error(f"Ошибка при архивировании изображений: {e}")
        await message.reply("Ошибка при создании архива с изображениями.")
    finally:
        if os.path.exists(archive_path):
            os.remove(archive_path)
            logging.info(f"Временный архив удален: {archive_name}")


@bot.on_message(filters.command("help"))
async def help_command(client, message):
    """
    Команда /help выводит список доступных команд для админа.
    Если пользователь не админ, выводится отказ.
    """
    if message.from_user.id != ADMIN_ID:
        await message.reply("Пошёл на хуй, ты не админ.")
        logging.warning(f"Неадминский запрос /help от пользователя {message.from_user.id}")
        return

    help_text = (
        "Список доступных команд для админа:\n"
        "/timeout <время> - установить глобальный тайм-аут для смены аватарки.\n"
        "/timeout_user <@username или id> <время> - установить тайм-аут для конкретного пользователя.\n"
        "/stop_spam - заблокировать смену аватарки для всех пользователей.\n"
        "/start_spam - разрешить смену аватарки для всех пользователей.\n"
        "/ban_user <@username или id> - забанить пользователя.\n"
        "/unban_user <@username или id> - разбанить пользователя.\n"
        "/logs - выгрузить логи (выбор файла через кнопки).\n"
        "/images - выгрузить архив с аватарками.\n"
        "/help - показать это сообщение."
    )
    await message.reply(help_text)
    logging.info(f"Отправлено сообщение /help для админа {message.from_user.id}")


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
# UPD 02/16/25 - ИХХИХИХИХИХХИ

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
