#!/usr/bin/env python3
"""
fix_foreign_leak_live.py — лечит конкретные уже ЗАПЛАНИРОВАННЫЕ (но ещё не
опубликованные) посты в реальном Telegram, в которых был найден баг "разорванный
смешанный текст" (кириллица+латиница в одном слове) — тот самый класс багов,
который только что был исправлен в коде (hasForeignLeak в index.html), но который
уже успел проскочить в реальное расписание ДО фикса, на старых постах. Эти два
поста уже стоят в очереди @ricar_telegrama:

  id=21 (23.06 ~07:00 Riga): "...последняя из правивших dynastии Ptolemaиov."
  id=54 (29.06 ~11:00 Riga): "...Битва при Агинорте, fought между римской..."
    (плюс искажённое название битвы — реальное сражение Октавиана и Антония
    в 31 г. до н.э. называется битва при Акциуме, не "Агинорт")

Правим текст напрямую через client.edit_message (как в dedupe_schedule.py) —
только текст, время/медиа не трогаем.
"""
import asyncio, os
from telethon import TelegramClient
from telethon.tl.functions.messages import GetScheduledHistoryRequest

BASE = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.join(BASE, "tg_user_session")
API_ID = 39578814
API_HASH = "18f9ab304c0119a6ab28ff913f02f192"
CHANNEL = "@ricar_telegrama"

FIXES = {
    21: "👸😮 Клеопатра — последний фараон Египта.\nФактически, она последняя из правивших династии Птолемеев.",
    54: "🚢💔 Армия сдалась, но только потому, что перепутали время.\n\nБитва при Акциуме, произошедшая между римской армией под командованием Октавиана Августа и войсками его противника Марка Антония, закончилась в 31 году до н.э. После долгой осады флот Антония, перепутав сигналы, начал отступление в неподходящий момент, что стоило ему победы.",
}


async def main():
    if not os.path.exists(SESSION + ".session"):
        print("❌ Telethon сессия не найдена.")
        return
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Сессия не авторизована.")
        await client.disconnect()
        return

    entity = await client.get_entity(CHANNEL)
    raw = await client(GetScheduledHistoryRequest(peer=entity, hash=0))
    msgs = {m.id: m for m in raw.messages if hasattr(m, "id")}

    for mid, new_text in FIXES.items():
        m = msgs.get(mid)
        if not m:
            print(f"  ⚠️ id={mid} не найден в текущем расписании (возможно уже опубликован/удалён) — пропускаю")
            continue
        old_preview = (m.message or "")[:60].replace("\n", " ")
        try:
            await client.edit_message(entity, mid, text=new_text, schedule=m.date)
            print(f"  ✅ id={mid} исправлен. Было: {old_preview!r}")
        except Exception as e:
            print(f"  ❌ id={mid} не удалось исправить: {e}")
        await asyncio.sleep(1.5)

    await client.disconnect()
    print("\nГотово.")


if __name__ == "__main__":
    asyncio.run(main())
