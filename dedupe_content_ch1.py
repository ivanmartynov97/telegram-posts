#!/usr/bin/env python3
"""
dedupe_content_ch1.py — удаляет дубли по СОДЕРЖАНИЮ текста (не по времени) среди
уже запланированных (scheduled, ещё не вышедших) постов в @history_plus_facts.
Похожие на 60%+ по нормализованному тексту считаем дублями: оставляем САМЫЙ РАННИЙ
по дате публикации в группе, остальные удаляем через DeleteScheduledMessagesRequest.
"""
import asyncio, os, re
from telethon import TelegramClient
from telethon.tl.functions.messages import GetScheduledHistoryRequest, DeleteScheduledMessagesRequest

BASE = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.join(BASE, "tg_user_session")
API_ID = 39578814
API_HASH = "18f9ab304c0119a6ab28ff913f02f192"
CHANNEL = "@history_plus_facts"

def normalize(text):
    t = (text or "").lower()
    t = re.sub(r'[^\w\sа-яёa-z0-9]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def similarity(a, b):
    wa, wb = set(normalize(a).split()), set(normalize(b).split())
    if not wa or not wb:
        return 0.0
    inter = len(wa & wb)
    return inter / max(len(wa), len(wb))

async def main():
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Не авторизован.")
        return
    entity = await client.get_entity(CHANNEL)
    raw = await client(GetScheduledHistoryRequest(peer=entity, hash=0))
    msgs = [m for m in raw.messages if hasattr(m, "id") and getattr(m, "message", None)]
    msgs.sort(key=lambda m: m.date)
    print(f"Всего отложенных постов: {len(msgs)}")

    used = set()
    to_delete = []
    groups = []
    for i, m in enumerate(msgs):
        if m.id in used:
            continue
        group = [m]
        used.add(m.id)
        for m2 in msgs[i+1:]:
            if m2.id in used:
                continue
            if similarity(m.message, m2.message) >= 0.6:
                group.append(m2)
                used.add(m2.id)
        if len(group) > 1:
            groups.append(group)

    print(f"Найдено групп дублей: {len(groups)}")
    for g in groups:
        keep = g[0]
        dupes = g[1:]
        preview = (keep.message or "")[:50].replace("\n", " ")
        print(f"  Группа ({len(g)} постов), оставляем id={keep.id} [{keep.date}] {preview!r}")
        for d in dupes:
            print(f"    -> удаляем id={d.id} [{d.date}]")
            to_delete.append(d.id)

    if to_delete:
        await client(DeleteScheduledMessagesRequest(peer=entity, id=to_delete))
        print(f"\n✅ Удалено {len(to_delete)} дублей-копий (id): {to_delete}")
    else:
        print("\nℹ️ Дублей не найдено.")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
