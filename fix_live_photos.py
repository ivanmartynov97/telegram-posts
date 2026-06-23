#!/usr/bin/env python3
"""БАГ-ФИКС: часть уже отложенных постов в LIVE расписании Telegram показывают картинку
как файл-документ, а не как обычное фото. Причина: send_file получал AI-картинку
(Pollinations) просто как URL-строку без расширения файла — Telethon решает фото/документ
по расширению имени и без .jpg/.png отправлял как обычный документ. auto_publish.py уже
пофикшен на будущее (скачивает и оборачивает в BytesIO с .name="photo.jpg"). Этот скрипт
точечно чинит то, что уже стоит в расписании: находит документы среди отложенных постов,
скачивает их, удаляет старое отложенное сообщение и пересоздаёт на то же время как фото."""
import asyncio, os, io
from telethon import TelegramClient
from telethon.tl.functions.messages import GetScheduledHistoryRequest, DeleteScheduledMessagesRequest
from telethon.tl.types import MessageMediaDocument

BASE = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.join(BASE, "tg_user_session")
API_ID = 39578814
API_HASH = "18f9ab304c0119a6ab28ff913f02f192"

CHANNELS = ["@fact_po_secretu", "@umnaya_utka", "@history_plus_facts", "@ricar_telegrama"]


async def main():
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Telethon не авторизован")
        return

    for uname in CHANNELS:
        print(f"\n=== {uname} ===")
        entity = await client.get_entity(uname)
        raw = await client(GetScheduledHistoryRequest(peer=entity, hash=0))
        bad = [m for m in raw.messages if isinstance(getattr(m, "media", None), MessageMediaDocument)]
        print(f"  Найдено отложенных постов с картинкой-как-файлом: {len(bad)}")
        for m in bad:
            try:
                data = await client.download_media(m, file=bytes)
                buf = io.BytesIO(data)
                buf.name = "photo.jpg"
                caption = m.message
                sched_dt = m.date
                await client(DeleteScheduledMessagesRequest(peer=entity, id=[m.id]))
                await client.send_file(entity, file=buf, caption=caption, schedule=sched_dt, parse_mode="html", force_document=False)
                print(f"  ✅ пересоздан как фото: id={m.id} [{sched_dt}] {(caption or '')[:50]!r}")
            except Exception as e:
                print(f"  ❌ не смог пересоздать id={m.id}: {e}")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
