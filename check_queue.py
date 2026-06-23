#!/usr/bin/env python3
"""
Проверяет количество постов в очереди.
Если меньше порога — отправляет уведомление админу в Telegram.
Запускается ежедневно через launchd.
"""

import json, os, ssl, logging
import urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

BASE       = os.path.dirname(os.path.abspath(__file__))
CONFIG     = os.path.join(BASE, "config.json")
LOG_PATH   = os.path.join(BASE, "check_queue.log")
QUEUE_DIR  = os.path.join(BASE, "queue")
THRESHOLD  = 7  # уведомление если постов меньше этого числа

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

def main():
    with open(CONFIG) as f:
        cfg = json.load(f)

    token    = cfg["bot_token"]
    admin_id = cfg.get("admin_chat_id")

    if not admin_id:
        logging.error("admin_chat_id не задан в config.json")
        print("Ошибка: добавь admin_chat_id в config.json")
        print("Узнать свой ID: напиши боту @userinfobot в Telegram")
        return

    import glob
    posts = glob.glob(os.path.join(QUEUE_DIR, "*.json"))
    count = len(posts)

    logging.info(f"Постов в очереди: {count}")
    print(f"Постов в очереди: {count}")

    if count < THRESHOLD:
        now = datetime.now(timezone(timedelta(hours=3)))
        msg = (
            f"⚠️ <b>Очередь заканчивается!</b>\n\n"
            f"В очереди осталось <b>{count}</b> постов.\n"
            f"Нужно добавить новые — иначе канал замолчит.\n\n"
            f"📅 {now.strftime('%d.%m.%Y %H:%M')} (Рига)"
        )
        res = send_message(token, admin_id, msg)
        if res.get("ok"):
            logging.info(f"Уведомление отправлено (постов: {count})")
            print("✅ Уведомление отправлено")
        else:
            logging.error(f"Ошибка отправки: {res}")
            print(f"❌ Ошибка: {res}")
    else:
        print(f"✅ Всё ок, постов достаточно ({count} >= {THRESHOLD})")

if __name__ == "__main__":
    main()
