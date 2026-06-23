#!/usr/bin/env python3
"""
Проверяет есть ли незаполненные слоты ЗАВТРА.
Если есть — отправляет уведомление в Telegram за 24 часа.
Запускается ежедневно в 20:00 через launchd.
"""

import json, os, ssl, glob, logging
import urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

BASE       = os.path.dirname(os.path.abspath(__file__))
CONFIG     = os.path.join(BASE, "config.json")
LOG_PATH   = os.path.join(BASE, "check_empty_days.log")
QUEUE_DIR  = os.path.join(BASE, "queue")
GH_REPO    = "ivanmartynov97/telegram-posts"

HOURS      = [7, 11, 13, 16, 18, 22]  # слоты публикации
RIGA_TZ    = timezone(timedelta(hours=3))

logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format="%(asctime)s %(message)s")

def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def send_message(token, chat_id, text):
    url  = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST",
          headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=10, context=ssl_ctx()) as r:
        return json.loads(r.read())

def gh_get_queue(token):
    """Получает список файлов очереди из GitHub."""
    url = f"https://api.github.com/repos/{GH_REPO}/contents/queue"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    })
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        files = json.loads(r.read())
    return [f for f in files if f["name"].endswith(".json") and not f["name"].startswith("reserve")]

def download_json(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10, context=ssl_ctx()) as r:
        return json.loads(r.read())

def makeSlots(n):
    """Воспроизводит логику makeSlots из JS — генерирует расписание."""
    slots = []
    now = datetime.now(RIGA_TZ)
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    while len(slots) < n:
        for h in HOURS:
            dt = day.replace(hour=h)
            if dt > now + timedelta(minutes=3):
                slots.append(dt)
                if len(slots) == n:
                    break
        day += timedelta(days=1)
    return slots

def main():
    with open(CONFIG) as f:
        cfg = json.load(f)

    bot_token = cfg["bot_token"]
    gh_token  = cfg.get("github_token")
    admin_id  = cfg.get("admin_chat_id")

    if not admin_id:
        logging.error("admin_chat_id не задан в config.json")
        return
    if not gh_token:
        logging.error("github_token не задан в config.json")
        return

    now_riga = datetime.now(RIGA_TZ)
    tomorrow = (now_riga + timedelta(days=1)).date()
    logging.info(f"Проверяю слоты на завтра: {tomorrow}")

    # Получаем очередь из GitHub
    try:
        files = gh_get_queue(gh_token)
    except Exception as e:
        # Фолбэк: читаем локальные файлы
        logging.warning(f"GitHub недоступен, читаю локально: {e}")
        files = None

    # Генерируем расписание как в JS
    n = len(files) if files else len(glob.glob(os.path.join(QUEUE_DIR, "*.json")))
    if n == 0:
        msg = (f"🚨 <b>Очередь пуста!</b>\n\n"
               f"Постов нет вообще. Срочно добавь контент!\n"
               f"📅 {now_riga.strftime('%d.%m.%Y %H:%M')} (Рига)")
        send_message(bot_token, admin_id, msg)
        logging.info("Очередь пуста — отправил алерт")
        return

    slots = makeSlots(n)

    # Находим слоты на завтра
    tomorrow_slots = [s for s in slots if s.date() == tomorrow]
    all_tomorrow   = [h for h in HOURS]  # все 6 возможных слотов завтра
    filled_hours   = {s.hour for s in tomorrow_slots}
    empty_hours    = [h for h in all_tomorrow if h not in filled_hours]

    logging.info(f"Завтра слотов заполнено: {len(filled_hours)}/6, пустых: {len(empty_hours)}")

    if not empty_hours:
        logging.info("Завтра всё заполнено — уведомление не нужно")
        print(f"✅ Завтра ({tomorrow}) все слоты заполнены")
        return

    # Форматируем список незаполненных часов
    empty_str = ", ".join(f"{h}:00" for h in empty_hours)
    filled_str = ", ".join(f"{h}:00" for h in sorted(filled_hours)) or "нет"

    msg = (
        f"⚠️ <b>Завтра есть пустые слоты!</b>\n\n"
        f"📅 <b>{tomorrow.strftime('%d.%m.%Y')}</b>\n\n"
        f"✅ Заполнены: {filled_str}\n"
        f"❌ Пустые: <b>{empty_str}</b>\n\n"
        f"Заполни очередь в мини-апп чтобы канал не молчал завтра."
    )

    res = send_message(bot_token, admin_id, msg)
    if res.get("ok"):
        logging.info(f"Уведомление отправлено: пустые {empty_str}")
        print(f"✅ Уведомлено: завтра пустые слоты {empty_str}")
    else:
        logging.error(f"Ошибка отправки: {res}")
        print(f"❌ Ошибка: {res}")

if __name__ == "__main__":
    main()
