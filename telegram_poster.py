#!/usr/bin/env python3
"""
Берёт первый файл из папки queue/, публикует в Telegram, удаляет файл.
Поддерживает форматы:
  - .json: {"text": "...", "image_url": "..."} → sendPhoto с подписью
  - .txt:  просто текст → sendMessage (обратная совместимость)
Запускается через launchd 6 раз в день.
"""

import urllib.request
import urllib.parse
import json
import os
import ssl
import logging
import glob

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, "config.json")
QUEUE_DIR = os.path.join(BASE, "queue")
LOG_PATH = os.path.join(BASE, "poster.log")

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(message)s"
)

def get_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def send_message(cfg, text):
    url = f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": cfg["channel_id"],
        "text": text,
        "parse_mode": "HTML"
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                  headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=15, context=get_ssl_context()) as resp:
        return json.loads(resp.read())

def send_photo(cfg, image_url, caption):
    url = f"https://api.telegram.org/bot{cfg['bot_token']}/sendPhoto"
    data = urllib.parse.urlencode({
        "chat_id": cfg["channel_id"],
        "photo": image_url,
        "caption": caption,
        "parse_mode": "HTML"
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                  headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=15, context=get_ssl_context()) as resp:
        return json.loads(resp.read())

def main():
    # Берём файлы очереди, сортируем по имени
    files = sorted(
        glob.glob(os.path.join(QUEUE_DIR, "*.json")) +
        glob.glob(os.path.join(QUEUE_DIR, "*.txt"))
    )

    if not files:
        logging.warning("⚠️ Очередь пуста — нечего публиковать")
        return

    next_file = files[0]
    remaining = len(files) - 1

    with open(CONFIG_PATH) as f:
        cfg = json.load(f)

    # Определяем формат и отправляем
    if next_file.endswith(".json"):
        with open(next_file, encoding="utf-8") as f:
            post = json.load(f)
        text = post.get("text", "").strip()
        image_url = post.get("image_url", "").strip()

        if not text:
            os.remove(next_file)
            logging.warning(f"⚠️ {next_file} пуст — пропускаю")
            return

        if image_url:
            try:
                result = send_photo(cfg, image_url, text)
            except Exception as e:
                logging.warning(f"⚠️ Не удалось отправить фото ({e}), отправляю текстом")
                result = send_message(cfg, text)
        else:
            result = send_message(cfg, text)

    else:  # .txt
        text = open(next_file, encoding="utf-8").read().strip()
        if not text:
            os.remove(next_file)
            logging.warning(f"⚠️ {next_file} пуст — пропускаю")
            return
        result = send_message(cfg, text)

    if result.get("ok"):
        msg_id = result["result"]["message_id"]
        logging.info(f"✅ message_id={msg_id} | осталось: {remaining} | {text[:60]}...")
        os.remove(next_file)
        if remaining < 6:
            logging.warning(f"⚠️ В очереди мало постов ({remaining}) — пора генерировать!")
    else:
        logging.error(f"❌ Ошибка Telegram: {result}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"❌ Исключение: {e}")
        raise
