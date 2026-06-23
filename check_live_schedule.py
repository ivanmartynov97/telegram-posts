#!/usr/bin/env python3
"""Диагностика: показывает РЕАЛЬНОЕ состояние расписания Telegram для обоих
каналов через сырой GetScheduledHistoryRequest (надёжнее чем client.get_messages
(scheduled=True), который недосчитывает в этом окружении). Ничего не меняет."""
import asyncio, json, os, base64
import urllib.request
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.tl.functions.messages import GetScheduledHistoryRequest

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "config.json")
SESSION = os.path.join(BASE, "tg_user_session")
API_ID = 39578814
API_HASH = "18f9ab304c0119a6ab28ff913f02f192"
RIGA_TZ = timezone(timedelta(hours=3))

def dump_queue(gh_token, gh_repo, queue_dir):
    url = f"https://api.github.com/repos/{gh_repo}/contents/{queue_dir}"
    req = urllib.request.Request(url, headers={"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"})
    try:
        items = json.loads(urllib.request.urlopen(req, timeout=15).read())
    except Exception as e:
        print(f"  ОШИБКА список {queue_dir}: {e}")
        return
    items = [it for it in items if it["type"] == "file" and it["name"].endswith(".json")]
    print(f"\n--- GitHub очередь {queue_dir}/: {len(items)} файлов ---")
    rows = []
    for it in sorted(items, key=lambda x: x["name"]):
        try:
            fr = urllib.request.Request(it["url"], headers={"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"})
            data = json.loads(urllib.request.urlopen(fr, timeout=15).read())
            post = json.loads(base64.b64decode(data["content"]).decode("utf-8"))
            sa = post.get("scheduled_at", "")
            txt = (post.get("text") or "")[:40].replace("\n", " ")
            rows.append((sa or "—", it["name"], txt))
        except Exception as e:
            rows.append(("?", it["name"], f"ОШИБКА чтения: {e}"))
    for sa, name, txt in sorted(rows, key=lambda r: r[0]):
        print(f"  {sa:25s} {name:30s} {txt!r}")

async def main():
    with open(CONFIG) as f:
        cfg = json.load(f)
    gh_token = cfg.get("github_token", "")
    gh_repo = cfg.get("github_repo", "ivanmartynov97/telegram-posts")
    channels = cfg.get("channels") or [{"channel_id": cfg["channel_id"], "queue_dir": "queue"}]

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("NOT AUTHORIZED")
        return
    me = await client.get_me()
    print(f"Авторизован как {me.first_name} (@{me.username})")
    now = datetime.now(RIGA_TZ)
    print(f"Сейчас: {now.strftime('%d.%m %H:%M %Z')}")

    for ch in channels:
        cid = ch["channel_id"]
        print(f"\n=== {cid} ===")
        try:
            entity = await client.get_entity(cid)
            raw = await client(GetScheduledHistoryRequest(peer=entity, hash=0))
            msgs = [m for m in raw.messages if hasattr(m, "date") and hasattr(m, "id")]
            msgs = sorted(msgs, key=lambda m: m.date)
            print(f"Всего в расписании (raw API): {len(msgs)}")
            for m in msgs:
                d = m.date.astimezone(RIGA_TZ)
                preview = (m.message or "")[:55].replace("\n"," ")
                print(f"  id={m.id}  {d.strftime('%d.%m %H:%M')}  {preview!r}")
        except Exception as e:
            print(f"ОШИБКА: {e}")

        dump_queue(gh_token, gh_repo, ch.get("queue_dir", "queue"))

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
