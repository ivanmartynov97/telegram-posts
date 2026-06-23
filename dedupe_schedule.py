#!/usr/bin/env python3
"""
dedupe_schedule.py — лечит уже накопившийся побочный эффект бага в auto_publish.py
(до фикса в коммите 40b27fa make_slots() не знал о слотах, занятых предыдущими
запусками каждые 30 минут, поэтому несколько разных постов могли получить ОДНО
и то же время — отсюда "2 поста в одну минуту" в канале).

Сам баг в коде уже исправлен. Этот скрипт чинит ПОСЛЕДСТВИЯ: проходит по уже
ПОСТАВЛЕННЫМ в расписание Telegram постам (которые ещё не вышли — scheduled=True)
для каждого канала, находит те, что случайно попали на одно и то же время, и
переносит лишние на следующий свободный слот по тому же расписанию (07/11/13/16/18/22),
НЕ удаляя и не теряя ни одного поста — только меняет время.

Текст и фото поста не трогаются: при переносе явно передаём обратно тот же
text + formatting_entities, медиа не указываем вообще, чтобы Telegram его не менял.

Сначала запусти БЕЗ --apply — увидишь, что будет сделано, ничего не меняя.
Когда убедишься, что план разумный, запусти ещё раз с --apply.
"""
import asyncio, json, os, sys
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.tl.functions.messages import GetScheduledHistoryRequest

BASE    = os.path.dirname(os.path.abspath(__file__))
CONFIG  = os.path.join(BASE, "config.json")
SESSION = os.path.join(BASE, "tg_user_session")

API_ID     = 39578814
API_HASH   = "18f9ab304c0119a6ab28ff913f02f192"
RIGA_TZ    = timezone(timedelta(hours=3))
POST_HOURS = [7, 11, 13, 16, 18, 22]


def next_free_slot(used: set, start_after: datetime) -> datetime:
    day = start_after.astimezone(RIGA_TZ).date()
    while True:
        for h in POST_HOURS:
            dt = datetime(day.year, day.month, day.day, h, 0, 0, tzinfo=RIGA_TZ)
            if dt > start_after and dt not in used:
                return dt
        day += timedelta(days=1)


async def dedupe(client, channel_id, label, apply_changes):
    entity = await client.get_entity(channel_id)

    raw = await client(GetScheduledHistoryRequest(peer=entity, hash=0))
    msgs = [m for m in raw.messages if hasattr(m, "date") and hasattr(m, "id")]
    msgs = sorted(msgs, key=lambda m: m.date)
    print(f"\n=== {label} ({channel_id}) — запланировано всего (raw API): {len(msgs)} ===")
    if os.environ.get("DEDUPE_DEBUG"):
        for m in msgs:
            print(f"    debug id={m.id} {m.date.astimezone(RIGA_TZ).strftime('%d.%m %H:%M')}  {(m.message or '')[:40]!r}")

    used_times = set(m.date for m in msgs)
    seen = set()
    moved = 0
    now_riga = datetime.now(RIGA_TZ)

    for m in msgs:
        t = m.date
        if t not in seen:
            seen.add(t)
            continue

        # дубль слота — переносим этот пост на следующий свободный
        new_dt = next_free_slot(used_times, max(t, now_riga + timedelta(minutes=15)))
        used_times.add(new_dt)
        old_str = t.astimezone(RIGA_TZ).strftime("%d.%m %H:%M")
        new_str = new_dt.strftime("%d.%m %H:%M")
        preview = (m.message or "")[:45].replace("\n", " ")

        if not apply_changes:
            print(f"  [DRY] id={m.id}: {old_str} → {new_str}  — {preview}...")
            moved += 1
            continue

        try:
            await client.edit_message(
                entity, m.id,
                text=m.message or "",
                formatting_entities=m.entities,
                schedule=new_dt,
            )
            print(f"  ↪ id={m.id}: {old_str} → {new_str}  — {preview}...")
            moved += 1
        except Exception as e:
            print(f"  ❌ id={m.id} перенос не удался: {e}")
        await asyncio.sleep(1.5)

    print(f"{label}: дублей слотов {'найдено' if not apply_changes else 'перенесено'}: {moved}")


async def main():
    apply_changes = "--apply" in sys.argv
    with open(CONFIG) as f:
        cfg = json.load(f)
    channels = cfg.get("channels") or [{"channel_id": cfg["channel_id"]}]

    if not os.path.exists(SESSION + ".session"):
        print("❌ Telethon сессия не найдена.")
        return

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Сессия не авторизована.")
        await client.disconnect()
        return

    print("🔍 DRY-RUN" if not apply_changes else "✏️  ПРИМЕНЯЮ ИЗМЕНЕНИЯ", "(добавь --apply чтобы реально перенести)" if not apply_changes else "")

    for ch in channels:
        await dedupe(client, ch["channel_id"], ch["channel_id"], apply_changes)

    await client.disconnect()
    print("\nГотово.")


if __name__ == "__main__":
    asyncio.run(main())
