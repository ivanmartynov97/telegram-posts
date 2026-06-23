#!/usr/bin/env python3
"""
Читает все посты из папки queue/ и отправляет их в Telegram
как отложенные сообщения (schedule_date).
После отправки файлы из очереди удаляются.

Запуск: python3 schedule_posts.py

Время публикации (Рига, UTC+3):
  7:00, 11:00, 13:00, 16:00, 18:00, 22:00
"""

import urllib.request
import urllib.parse
import json
import os
import ssl
import glob
import sys
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, "config.json")
QUEUE_DIR  = os.path.join(BASE, "queue")

# Рига = UTC+3 летом (EEST)
RIGA_TZ = timezone(timedelta(hours=3))

# Времена публикации в часах по Риге
POST_HOURS = [7, 11, 13, 16, 18, 22]

def get_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def make_schedule(n_posts: int) -> list[int]:
    """
    Возвращает список Unix-timestamp (UTC) для n_posts постов,
    начиная с ближайшего слота в будущем.
    """
    now = datetime.now(RIGA_TZ)
    slots = []
    day = now.date()

    while len(slots) < n_posts:
        for h in POST_HOURS:
            dt = datetime(day.year, day.month, day.day, h, 0, 0, tzinfo=RIGA_TZ)
            # Берём только будущие слоты (минимум 5 минут вперёд)
            if dt > now + timedelta(minutes=5):
                slots.append(int(dt.timestamp()))
                if len(slots) == n_posts:
                    break
        day += timedelta(days=1)

    return slots

def api_request(token: str, method: str, params: dict) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                  headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=15, context=get_ssl_context()) as resp:
        return json.loads(resp.read())

def main():
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    token   = cfg["bot_token"]
    channel = cfg["channel_id"]

    # Собираем очередь
    files = sorted(
        glob.glob(os.path.join(QUEUE_DIR, "*.json")) +
        glob.glob(os.path.join(QUEUE_DIR, "*.txt"))
    )

    if not files:
        print("Очередь пуста. Сначала запусти генерацию постов.")
        sys.exit(1)

    print(f"Найдено постов в очереди: {len(files)}")
    timestamps = make_schedule(len(files))

    ok_count = 0
    fail_count = 0

    for i, (fpath, ts) in enumerate(zip(files, timestamps), 1):
        dt_riga = datetime.fromtimestamp(ts, tz=RIGA_TZ).strftime("%d.%m %H:%M")

        try:
            if fpath.endswith(".json"):
                with open(fpath, encoding="utf-8") as f:
                    post = json.load(f)
                text      = post.get("text", "").strip()
                image_url = post.get("image_url", "").strip()
            else:
                text      = open(fpath, encoding="utf-8").read().strip()
                image_url = ""

            if not text:
                print(f"  [{i}] Пропуск (пустой файл)")
                os.remove(fpath)
                continue

            if image_url:
                result = api_request(token, "sendPhoto", {
                    "chat_id":       channel,
                    "photo":         image_url,
                    "caption":       text,
                    "parse_mode":    "HTML",
                    "schedule_date": ts
                })
            else:
                result = api_request(token, "sendMessage", {
                    "chat_id":       channel,
                    "text":          text,
                    "parse_mode":    "HTML",
                    "schedule_date": ts
                })

            if result.get("ok"):
                print(f"  [{i}] ✅ {dt_riga} — {text[:50]}...")
                os.remove(fpath)
                ok_count += 1
            else:
                print(f"  [{i}] ❌ Ошибка: {result}")
                fail_count += 1

        except Exception as e:
            print(f"  [{i}] ❌ Исключение: {e}")
            fail_count += 1

    print(f"\nГотово: {ok_count} запланировано, {fail_count} ошибок.")
    print("Посты видны в разделе «Отложенные» твоего канала в Telegram.")

if __name__ == "__main__":
    main()
