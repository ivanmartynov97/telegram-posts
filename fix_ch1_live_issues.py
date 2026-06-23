#!/usr/bin/env python3
"""
fix_ch1_live_issues.py — лечит две конкретные находки в реальном расписании
@history_plus_facts, найденные при аудите queue_schedule_snapshot.json:

1. id=9 — тот же класс бага "слипшийся смешанный текст" (кириллица+латиница в
   одном слове), что уже чинили для @ricar_telegrama: "чемsoldаты" → "чем солдаты".

2. Шесть пар постов с ПОЛНОСТЬЮ одинаковым текстом, запланированных на РАЗНОЕ
   время (иногда в один и тот же день с разницей в 2-3 часа) — баг дедупликации
   тем, который должен был это предотвратить. Удаляем более позднюю копию каждой
   пары через DeleteScheduledMessagesRequest (для уже опубликованных обычный
   delete_messages не подходит — это именно ОТЛОЖЕННЫЕ сообщения, у них своя
   очередь id и свой метод удаления).
"""
import asyncio, os
from telethon import TelegramClient
from telethon.tl.functions.messages import GetScheduledHistoryRequest, DeleteScheduledMessagesRequest

BASE = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.join(BASE, "tg_user_session")
API_ID = 39578814
API_HASH = "18f9ab304c0119a6ab28ff913f02f192"
CHANNEL = "@history_plus_facts"

TEXT_FIX = {
    9: "📜 Самая короткая война между странами в истории не является рекордом для Австралии - её армия проиграла войну птицам. 27 августа 1932 года большая группа эму, крупных нелетающих птиц, напала на австралийских солдат, которые были вооружены пулеметами. Однако птицы оказались более сильными и ловкими, чем солдаты, и атака была вынуждена прекратить. Эта необычная битва стала предметом шуток и легенд в Австралии 🦃",
}

# Более поздняя копия каждой дублирующейся пары — её удаляем, более ранняя остаётся.
DUPLICATE_IDS_TO_DELETE = [25, 26, 27, 28, 30, 14]


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

    for mid, new_text in TEXT_FIX.items():
        m = msgs.get(mid)
        if not m:
            print(f"  ⚠️ id={mid} не найден (возможно уже опубликован) — пропускаю фикс текста")
            continue
        old_preview = (m.message or "")[:60].replace("\n", " ")
        try:
            await client.edit_message(entity, mid, text=new_text, schedule=m.date)
            print(f"  ✅ id={mid} текст исправлен. Было: {old_preview!r}")
        except Exception as e:
            print(f"  ❌ id={mid} не удалось исправить текст: {e}")
        await asyncio.sleep(1.5)

    to_delete = [mid for mid in DUPLICATE_IDS_TO_DELETE if mid in msgs]
    missing = [mid for mid in DUPLICATE_IDS_TO_DELETE if mid not in msgs]
    if missing:
        print(f"  ℹ️ уже не в расписании (видимо опубликованы/удалены ранее): {missing}")
    if to_delete:
        try:
            await client(DeleteScheduledMessagesRequest(peer=entity, id=to_delete))
            print(f"  🗑️ удалены дубли-копии (id): {to_delete}")
        except Exception as e:
            print(f"  ❌ не удалось удалить дубли {to_delete}: {e}")

    await client.disconnect()
    print("\nГотово.")


if __name__ == "__main__":
    asyncio.run(main())
