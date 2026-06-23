#!/usr/bin/env python3
"""
Отправляет текстовый пост в Telegram канал.
Использование: python3 post_to_telegram.py "Текст поста"
Или через stdin: echo "Текст" | python3 post_to_telegram.py
"""

import sys
import json
import urllib.request
import urllib.parse
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def send_message(bot_token: str, channel_id: str, text: str) -> dict:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": channel_id,
        "text": text,
        "parse_mode": "HTML"
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def main():
    config = load_config()

    # Текст из аргумента или stdin
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = sys.stdin.read().strip()

    if not text:
        print("Ошибка: текст пуст", file=sys.stderr)
        sys.exit(1)

    result = send_message(config["bot_token"], config["channel_id"], text)

    if result.get("ok"):
        print(f"✅ Опубликовано. message_id={result['result']['message_id']}")
    else:
        print(f"❌ Ошибка: {result}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
