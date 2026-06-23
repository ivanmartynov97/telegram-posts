#!/usr/bin/env python3
"""Диагностика: что реально лежит в queue3/queue4 на GitHub + что реально стоит
в LIVE расписании Telegram для @fact_po_secretu и @umnaya_utka (после того как
обнаружилось, что авто-пополнение мини-аппа залило исторические посты в факт-канал)."""
import asyncio, json, os, base64, ssl, urllib.request
from telethon import TelegramClient
from telethon.tl.functions.messages import GetScheduledHistoryRequest

BASE = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.join(BASE, "tg_user_session")
API_ID = 39578814
API_HASH = "18f9ab304c0119a6ab28ff913f02f192"

with open(os.path.join(BASE, "config.json")) as f:
    cfg = json.load(f)
GH_TOKEN = cfg["github_token"]
GH_REPO = "ivanmartynov97/telegram-posts"


def ssl_ctx():
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    return ctx


def gh_list(path):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"})
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
            return json.loads(r.read())
    except Exception as e:
        return []


def gh_get(path):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        d = json.loads(r.read())
    return json.loads(base64.b64decode(d["content"]).decode()), d["sha"]


def gh_delete(path, sha, msg):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    body = json.dumps({"message": msg, "sha": sha}).encode()
    req = urllib.request.Request(url, data=body, method="DELETE", headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return r.status


HISTORY_HINTS = ["войн", "импери", "король", "царь", "древн", "битв", "крепост", "столиц", "континент", "голливуд", "президент", "революци", "ковчег", "космонавт", "детектив", "корабл"]


def looks_historical(text):
    t = (text or "").lower()
    return any(h in t for h in HISTORY_HINTS)


async def main():
    print("=== GitHub queue3 (Факт по секрету) ===")
    for it in gh_list("queue3"):
        if it.get("type") != "file" or not it["name"].endswith(".json"):
            continue
        try:
            obj, sha = gh_get(it["path"])
        except Exception as e:
            print(f"  {it['name']}: ❌ не смог прочитать ({e})")
            continue
        flag = " ⚠️ ПОХОЖЕ НА ИСТОРИЮ" if looks_historical(obj.get("text")) else ""
        print(f"  {it['name']}: {(obj.get('text') or '')[:70]!r}{flag}")

    print("\n=== GitHub queue4 (Умная утка) ===")
    for it in gh_list("queue4"):
        if it.get("type") != "file" or not it["name"].endswith(".json"):
            continue
        try:
            obj, sha = gh_get(it["path"])
        except Exception as e:
            print(f"  {it['name']}: ❌ не смог прочитать ({e})")
            continue
        flag = " ⚠️ ПОХОЖЕ НА ИСТОРИЮ" if looks_historical(obj.get("text")) else ""
        print(f"  {it['name']}: {(obj.get('text') or '')[:70]!r}{flag}")

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("\n❌ Telethon не авторизован — не могу проверить LIVE расписание Telegram.")
        await client.disconnect()
        return

    for uname in ["@fact_po_secretu", "@umnaya_utka"]:
        print(f"\n=== LIVE расписание Telegram {uname} ===")
        try:
            entity = await client.get_entity(uname)
            raw = await client(GetScheduledHistoryRequest(peer=entity, hash=0))
            msgs = [m for m in raw.messages if hasattr(m, "id") and getattr(m, "message", None)]
            msgs.sort(key=lambda m: m.date)
            print(f"  Всего отложенных постов: {len(msgs)}")
            for m in msgs:
                flag = " ⚠️ ПОХОЖЕ НА ИСТОРИЮ" if looks_historical(m.message) else ""
                print(f"    id={m.id} [{m.date}] {(m.message or '')[:70]!r}{flag}")
        except Exception as e:
            print(f"  ⚠️ ошибка: {e}")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
