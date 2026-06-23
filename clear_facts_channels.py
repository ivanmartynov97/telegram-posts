#!/usr/bin/env python3
"""
clear_facts_channels.py — удаляет ВСЕ отложенные посты из Telegram (queue3/queue4)
и все файлы из этих папок на GitHub. Запускать перед перегенерацией фактов.
"""
import asyncio, json, os, base64, ssl, time, urllib.request

from telethon import TelegramClient
from telethon.tl.functions.messages import GetScheduledHistoryRequest, DeleteScheduledMessagesRequest

BASE    = os.path.dirname(os.path.abspath(__file__))
CONFIG  = os.path.join(BASE, "config.json")
SESSION = os.path.join(BASE, "tg_user_session")
API_ID  = 39578814
API_HASH = "18f9ab304c0119a6ab28ff913f02f192"

with open(CONFIG) as f:
    cfg = json.load(f)

GH_TOKEN = cfg["github_token"]
GH_REPO  = cfg.get("github_repo", "ivanmartynov97/telegram-posts")

# Каналы фактов: queue3 = @fact_po_secretu, queue4 = @umnaya_utka
FACT_CHANNELS = [
    ch for ch in cfg.get("channels", [])
    if ch.get("queue_dir") in ("queue3", "queue4")
]

def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def gh_headers():
    return {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}

def gh_list(qdir):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{qdir}"
    req = urllib.request.Request(url, headers=gh_headers())
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
            return json.loads(r.read())
    except Exception:
        return []

def gh_delete(path, sha, msg):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    payload = {"message": msg, "sha": sha}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="DELETE",
        headers={**gh_headers(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())

def clear_github_queue(qdir):
    print(f"\n── GitHub: чищу {qdir}/ ──")
    items = gh_list(qdir)
    files = [it for it in items if it.get("type") == "file" and it["name"].endswith(".json")]
    print(f"  Файлов в очереди: {len(files)}")
    deleted = 0
    for f in files:
        try:
            gh_delete(f["path"], f["sha"], f"Clear facts queue: {f['name']}")
            print(f"  🗑 {f['name']}")
            deleted += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"  ❌ {f['name']}: {e}")
    print(f"  Удалено: {deleted}/{len(files)}")

async def clear_telegram_channel(client, channel_id, label):
    print(f"\n── Telegram: чищу {label} ({channel_id}) ──")
    try:
        entity = await client.get_entity(channel_id)
        raw = await client(GetScheduledHistoryRequest(peer=entity, hash=0))
        ids = [m.id for m in raw.messages]
        print(f"  Отложенных постов: {len(ids)}")
        if not ids:
            return
        # Telegram ограничивает удаление батчами по ~100
        chunk = 100
        for i in range(0, len(ids), chunk):
            batch = ids[i:i+chunk]
            await client(DeleteScheduledMessagesRequest(peer=entity, id=batch))
            print(f"  🗑 удалено {len(batch)} постов")
            await asyncio.sleep(1)
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")

async def main():
    print("=== Очистка каналов фактов (Telegram + GitHub) ===\n")

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Telethon сессия не авторизована. Запусти auth_phone.command")
        await client.disconnect()
        return

    me = await client.get_me()
    print(f"✅ Авторизован как {me.first_name}")

    for ch in FACT_CHANNELS:
        qdir      = ch["queue_dir"]
        channel   = ch["channel_id"]
        # 1. Удаляем из Telegram
        await clear_telegram_channel(client, channel, qdir)
        # 2. Удаляем из GitHub
        clear_github_queue(qdir)

    await client.disconnect()
    print("\n✅ Всё очищено. Теперь запускай генерацию новых постов.")

if __name__ == "__main__":
    asyncio.run(main())
