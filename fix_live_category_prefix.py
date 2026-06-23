#!/usr/bin/env python3
"""Точечный фикс уже отложенных в Telegram постов, которые были поставлены в расписание
ДО фикса промпта и поэтому начинаются с этикетки категории ("Природа:", "Секс:",
"Психология:", "Здоровье:", "Тело:") вместо крючка.
БАГ-ФИКС: Telethon client.edit_message() не умеет редактировать SCHEDULED-сообщения
("The specified message ID is invalid" — отдельное пространство id у отложенных
сообщений). Поэтому используем тот же надёжный путь что и для фикса фото-как-документ:
скачать медиа (если есть) → удалить старое отложенное сообщение → пересоздать с тем же
временем и медиа, но с очищенным текстом."""
import asyncio, os, re, io, shutil, time
from telethon import TelegramClient
from telethon.tl.functions.messages import GetScheduledHistoryRequest, DeleteScheduledMessagesRequest

BASE = os.path.dirname(os.path.abspath(__file__))
# БАГ-ФИКС: "database is locked" — параллельно работает auto_publish.py/cron, держащий
# sqlite-файл сессии открытым на запись. Чтобы не ждать и не конфликтовать, делаем
# одноразовую копию файла сессии (тот же ключ авторизации, Telegram не против двух
# локальных файлов с одним auth_key) и подключаемся через неё.
_orig_session = os.path.join(BASE, "tg_user_session.session")
SESSION = os.path.join(BASE, f"tg_fix_session_{int(time.time())}")
shutil.copyfile(_orig_session, SESSION + ".session")
API_ID = 39578814
API_HASH = "18f9ab304c0119a6ab28ff913f02f192"

CHANNELS = ["@fact_po_secretu", "@umnaya_utka"]
CATEGORY_RE = re.compile(r"^(\S+\s*)[А-ЯA-Z][а-яёa-zA-Z]{2,16}(?:\s[А-ЯA-Z][а-яёa-zA-Z]{2,16})?:\s+")


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
        fixed = 0
        for m in raw.messages:
            text = getattr(m, "message", None) or ""
            if not CATEGORY_RE.match(text):
                continue
            new_text = CATEGORY_RE.sub(r"\1", text)
            try:
                file_obj = None
                if getattr(m, "media", None):
                    data = await client.download_media(m, file=bytes)
                    file_obj = io.BytesIO(data)
                    file_obj.name = "photo.jpg"
                sched_dt = m.date
                await client(DeleteScheduledMessagesRequest(peer=entity, id=[m.id]))
                if file_obj:
                    await client.send_file(entity, file=file_obj, caption=new_text, schedule=sched_dt, parse_mode="html", force_document=False)
                else:
                    await client.send_message(entity, new_text, schedule=sched_dt, parse_mode="html")
                fixed += 1
                print(f"  ✅ пересоздан id={m.id} [{sched_dt}]: {new_text[:60]!r}")
            except Exception as e:
                print(f"  ❌ id={m.id}: не смог пересоздать ({e})")
        print(f"  Исправлено постов с этикеткой категории: {fixed}")

    await client.disconnect()
    try:
        os.remove(SESSION + ".session")
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(main())
