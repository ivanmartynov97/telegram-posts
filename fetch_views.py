#!/usr/bin/env python3
"""
Собирает просмотры (views) постов канала через Telethon (MTProto).
Запускается каждый час через launchd.
Обновляет analytics/{message_id}.json в GitHub.

Перед первым запуском: python3 setup_telethon.py
"""

import asyncio, json, os, ssl, base64, logging
import urllib.request
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest

BASE        = os.path.dirname(os.path.abspath(__file__))
CONFIG      = os.path.join(BASE, "config.json")
SESSION     = os.path.join(BASE, "tg_user_session")
LOG_PATH    = os.path.join(BASE, "fetch_views.log")
GH_REPO     = "ivanmartynov97/telegram-posts"
POSTS_LIMIT = 50  # сколько последних постов проверяем

logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format="%(asctime)s %(message)s")

def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def gh_request(method, path, gh_token, payload=None):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method,
          headers={"Authorization": f"token {gh_token}",
                   "Accept": "application/vnd.github.v3+json",
                   "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10, context=ssl_ctx()) as r:
        return json.loads(r.read())

def gh_get(path, gh_token):
    return gh_request("GET", path, gh_token)

def gh_put(path, content_str, sha, msg, gh_token):
    content = base64.b64encode(content_str.encode()).decode()
    payload = {"message": msg, "content": content}
    if sha:
        payload["sha"] = sha
    return gh_request("PUT", path, gh_token, payload)

def gh_create(path, content_str, msg, gh_token):
    content = base64.b64encode(content_str.encode()).decode()
    return gh_request("PUT", path, gh_token, {"message": msg, "content": content})

def load_analytics_index(gh_token):
    """Загружает все analytics/*.json из GitHub, возвращает dict {message_id: record}"""
    try:
        files = gh_request("GET", "analytics", gh_token)
        result = {}
        for f in files:
            if not f["name"].endswith(".json"):
                continue
            req = urllib.request.Request(f["download_url"] + "?t=1",
                  headers={"User-Agent": "HistoryBot"})
            with urllib.request.urlopen(req, timeout=10, context=ssl_ctx()) as r:
                rec = json.loads(r.read())
                mid = rec.get("message_id")
                if mid:
                    result[mid] = {"record": rec, "sha": f["sha"], "path": f["path"]}
        return result
    except Exception as e:
        logging.warning(f"Не удалось загрузить analytics index: {e}")
        return {}

def update_views_in_github(path, sha, record, gh_token):
    gh_put(path, json.dumps(record, ensure_ascii=False, indent=2),
           sha, f"Views update: {record['message_id']}", gh_token)

def spike_score(history):
    """Оценка всплеска: views за первый час"""
    if len(history) < 1:
        return 0
    # Берём первую точку как views_1h
    return history[0].get("views", 0)

async def main():
    with open(CONFIG) as f:
        cfg = json.load(f)
    channel  = cfg["channel_id"]
    gh_token = cfg.get("github_token", "")

    api_id   = 39578814
    api_hash = "18f9ab304c0119a6ab28ff913f02f192"

    if not gh_token:
        logging.error("github_token не задан в config.json")
        print("Ошибка: добавь github_token в config.json")
        return

    if not os.path.exists(SESSION + ".session"):
        logging.error("Сессия Telethon не найдена. Запусти setup_telethon.py")
        print("Ошибка: сначала запусти python3 setup_telethon.py")
        return

    logging.info("Старт fetch_views")
    print("Загружаю analytics из GitHub...")
    analytics = load_analytics_index(gh_token)
    logging.info(f"Загружено {len(analytics)} записей из analytics/")

    now_riga = datetime.now(timezone(timedelta(hours=3)))
    now_str  = now_riga.isoformat()

    client = TelegramClient(SESSION, api_id, api_hash)
    await client.connect()
    try:
        print(f"Подключён. Получаю последние {POSTS_LIMIT} постов канала...")
        messages = await client.get_messages(channel, limit=POSTS_LIMIT)
        logging.info(f"Получено {len(messages)} постов из канала")

        updated = 0
        created = 0

        for msg in messages:
            if not msg or not msg.id:
                continue
            views = getattr(msg, "views", 0) or 0
            mid   = msg.id

            # Время публикации
            pub_time = msg.date.astimezone(timezone(timedelta(hours=3)))
            hours_old = (now_riga - pub_time).total_seconds() / 3600

            if mid in analytics:
                # Обновляем существующую запись
                entry  = analytics[mid]
                record = entry["record"]

                # Добавляем точку в историю views
                history = record.get("views_history", [])
                # Не добавляем дубль если последняя точка та же
                if not history or history[-1].get("views") != views:
                    history.append({"ts": now_str, "views": views})
                    if len(history) > 48:  # храним до 48 часов
                        history = history[-48:]
                    record["views_history"] = history

                record["views_current"]  = views
                record["views_updated_at"] = now_str
                record["hours_since_pub"] = round(hours_old, 1)

                # Spike score = views в первый час (первая записанная точка)
                if hours_old <= 2 and not record.get("views_1h"):
                    record["views_1h"] = views
                record["spike_score"] = record.get("views_1h", history[0].get("views", 0) if history else 0)

                try:
                    update_views_in_github(entry["path"], entry["sha"], record, gh_token)
                    updated += 1
                    print(f"  ✅ msg {mid}: {views} views ({hours_old:.1f}h old)")
                    logging.info(f"Обновлено msg {mid}: {views} views")
                except Exception as e:
                    logging.warning(f"Ошибка обновления msg {mid}: {e}")

            else:
                # Новый пост которого ещё нет в analytics — создаём запись
                text = getattr(msg, "text", "") or getattr(msg, "caption", "") or ""
                record = {
                    "message_id": mid,
                    "text": text,
                    "scheduled_at": pub_time.isoformat(),
                    "hour": pub_time.hour,
                    "has_image": bool(getattr(msg, "photo", None) or getattr(msg, "media", None)),
                    "char_count": len(text),
                    "views_history": [{"ts": now_str, "views": views}],
                    "views_current": views,
                    "views_1h": views if hours_old <= 2 else None,
                    "spike_score": views if hours_old <= 2 else 0,
                    "hours_since_pub": round(hours_old, 1),
                    "views_updated_at": now_str,
                    "reactions": {},
                    "total_reactions": 0,
                    "reactions_updated_at": None
                }
                try:
                    gh_create(f"analytics/{mid}.json",
                              json.dumps(record, ensure_ascii=False, indent=2),
                              f"New analytics: {mid}", gh_token)
                    created += 1
                    print(f"  ✨ Новый msg {mid}: {views} views")
                    logging.info(f"Создана запись msg {mid}: {views} views")
                except Exception as e:
                    logging.warning(f"Ошибка создания записи {mid}: {e}")

        logging.info(f"Финиш: обновлено {updated}, создано {created}")
        print(f"\nГотово: обновлено {updated}, создано {created} записей.")
    finally:
        await client.disconnect()

asyncio.run(main())
