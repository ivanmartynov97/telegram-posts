#!/usr/bin/env python3
"""
add_quizzes.py — добавляет quiz-опросы "Правда/Ложь" в расписание канала.
Использует Telethon MTProto для создания викторин с объяснением.

Использование:
    python3 add_quizzes.py <queue5|queue3|queue4|queue2>
"""
import asyncio, json, os, sys, random, urllib.error
from datetime import datetime, timezone, timedelta

BASE    = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.join(BASE, "tg_user_session")

with open(os.path.join(BASE, "config.json")) as f:
    cfg = json.load(f)

API_ID   = cfg["api_id"]
API_HASH = cfg["api_hash"]

# Каналы по очередям
CHANNELS = {
    "queue2": "@ricar_telegrama",
    "queue3": "@fact_po_secretu",
    "queue4": "@umnaya_utka",
    "queue5": "@umnim_vhod",
}

# ─────────────────────────────────────────────────────────────────────────────
# ВИКТОРИНЫ ДЛЯ queue5 (@umnim_vhod) — правда/ложь о теле и психике
# ─────────────────────────────────────────────────────────────────────────────
QUIZZES_Q5 = [
    {
        "question": "🐱 Кошки умеют видеть в абсолютной темноте — там, где нет ни единого фотона света",
        "options": ["✅ Правда", "❌ Ложь"],
        "correct": 1,  # Ложь
        "explanation": "Кошки видят при очень слабом освещении — в 6 раз лучше человека. Но в абсолютной темноте без единого фотона они слепы так же, как и мы. Их секрет — tapetum lucidum: слой за сетчаткой, отражающий свет повторно."
    },
    {
        "question": "🧠 Человек использует только 10% своего мозга — остальные 90% молчат",
        "options": ["✅ Правда", "❌ Ложь"],
        "correct": 1,  # Ложь
        "explanation": "Миф. МРТ показывает: в течение дня активны ВСЕ области мозга. Просто разные зоны включаются в разные моменты. Мозг потребляет 20% энергии тела — эволюция не стала бы кормить 90% бесполезной ткани."
    },
    {
        "question": "😤 Когда ты злишься, твой мозг физически не может думать логично",
        "options": ["✅ Правда", "❌ Ложь"],
        "correct": 0,  # Правда
        "explanation": "Правда. При сильной злости амигдала подавляет активность префронтальной коры — центра логики. МРТ фиксирует снижение активности до 30%. Именно поэтому споры в гневе бессмысленны: вы буквально не в состоянии мыслить рационально."
    },
    {
        "question": "💊 Плацебо не работает, если человек знает, что принимает пустышку",
        "options": ["✅ Правда", "❌ Ложь"],
        "correct": 1,  # Ложь
        "explanation": "Ложь. Исследования Гарварда показали: 59% пациентов с хронической болью чувствовали облегчение даже зная, что принимают сахарную таблетку. Эффект работает через ожидание и нейронные механизмы — само слово «плацебо» уже запускает процесс."
    },
    {
        "question": "😴 Полное лишение сна убивает человека быстрее, чем голод",
        "options": ["✅ Правда", "❌ Ложь"],
        "correct": 0,  # Правда
        "explanation": "Правда. Без сна человек погибает примерно за 11 дней. Без еды — можно прожить 3-8 недель. Мировой рекорд без сна — 11 дней 25 минут (Рэнди Гарднер, 1964). К концу он галлюцинировал и не мог говорить."
    },
    {
        "question": "🍌 ДНК человека совпадает с ДНК банана примерно наполовину",
        "options": ["✅ Правда", "❌ Ложь"],
        "correct": 0,  # Правда
        "explanation": "Правда — около 60% генов совпадают. Это звучит дико, но базовые клеточные процессы — метаболизм, деление клеток, защита ДНК — появились миллиарды лет назад и сохранились у всех живых существ. С мышью мы совпадаем на 85%, с шимпанзе на 98%."
    },
    {
        "question": "👁️ Мы моргаем примерно 15–20 раз в минуту, но почти не замечаем этого",
        "options": ["✅ Правда", "❌ Ложь"],
        "correct": 0,  # Правда
        "explanation": "Правда. Мозг активно «вырезает» моменты моргания из восприятия — это называется мигательное подавление. Зрительная кора временно отключается, пока веко закрыто. За жизнь вы «теряете» около 1,5 лет в темноте от моргания."
    },
    {
        "question": "💋 Поцелуй длиннее 10 секунд передаёт партнёру больше 80 миллионов бактерий",
        "options": ["✅ Правда", "❌ Ложь"],
        "correct": 0,  # Правда
        "explanation": "Правда. Исследование 2014 года: за 10-секундный поцелуй передаётся от 10 до 80 миллионов бактерий. Но пугаться не стоит — большинство из них ваши собственные штаммы, живущие в слюне. Некоторые пары со временем синхронизируют микрофлору рта."
    },
    {
        "question": "⏱️ В момент смертельной опасности время замедляется, потому что мозг ускоряется",
        "options": ["✅ Правда", "❌ Ложь"],
        "correct": 1,  # Ложь
        "explanation": "Ложь. Мозг не ускоряется — он просто записывает воспоминания детальнее через амигдалу. Потом кажется, что прошло больше времени. Это доказали экспериментом: испытуемые падали с высоты — замедления реакции не было, только иллюзия в воспоминаниях."
    },
    {
        "question": "🫁 Человек физически не может задержать дыхание и умереть от этого",
        "options": ["✅ Правда", "❌ Ложь"],
        "correct": 0,  # Правда
        "explanation": "Правда. Когда CO₂ в крови достигает критического уровня, мозговой ствол насильно запускает вдох — против вашей воли. Потерять сознание от задержки дыхания можно, но умереть — нет. Мировой рекорд: 24 минуты 37 секунд (после гипервентиляции кислородом)."
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# ВИКТОРИНЫ ДЛЯ queue3 (@fact_po_secretu) — о животных
# ─────────────────────────────────────────────────────────────────────────────
QUIZZES_Q3 = [
    {
        "question": "🦈 Акулы — единственные рыбы, которые умеют моргать",
        "options": ["✅ Правда", "❌ Ложь"],
        "correct": 0,  # Правда
        "explanation": "Правда. У акул есть мигательная перепонка — третье веко, которое закрывается снизу во время атаки, защищая глаз. Большинство рыб не имеют век вообще. Некоторые акулы, у которых нет этой перепонки (белая акула), закатывают глаза назад при укусе."
    },
    {
        "question": "🐘 У слонов самая большая память среди животных — они никогда ничего не забывают",
        "options": ["✅ Правда", "❌ Ложь"],
        "correct": 1,  # Ложь
        "explanation": "Ложь — это преувеличение. Слоны действительно имеют отличную долгосрочную память: узнают людей через 10+ лет, помнят водоёмы за сотни километров. Но «никогда ничего не забывают» — миф. Мозг слона в 3 раза больше человеческого, но механизмы памяти те же."
    },
    {
        "question": "🐝 Пчела умирает сразу после того, как ужалила человека",
        "options": ["✅ Правда", "❌ Ложь"],
        "correct": 1,  # Ложь (не всегда)
        "explanation": "Ложь — не всегда. Жалящий аппарат застревает только в толстой коже млекопитающих (кожа пронизана слоями). При укусе других насекомых или тонкокожих существ пчела выдёргивает жало и выживает. Погибает только рабочая пчела, ужалив человека или животное."
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# ВИКТОРИНЫ ДЛЯ queue4 (@umnaya_utka) — о науке и природе
# ─────────────────────────────────────────────────────────────────────────────
QUIZZES_Q4 = [
    {
        "question": "🌍 Стекло — это твёрдое тело. Старые витражи снизу толще из-за того, что стекло «течёт» веками",
        "options": ["✅ Правда", "❌ Ложь"],
        "correct": 1,  # Ложь
        "explanation": "Ложь. Это популярный миф. Старинные витражи толще снизу потому, что средневековые стеклодувы не умели делать идеально ровные листы — при установке клали толстый конец вниз. Стекло — аморфное твёрдое тело, и при комнатной температуре оно не течёт. Время «течения» — триллионы лет."
    },
    {
        "question": "🌊 Мы знаем о поверхности Марса больше, чем о дне собственного океана",
        "options": ["✅ Правда", "❌ Ложь"],
        "correct": 0,  # Правда
        "explanation": "Правда. Картировано около 20% дна мирового океана. Поверхность Марса изучена с точностью до метра — орбитальные аппараты облетали его десятилетиями. Давление на дне (600 атмосфер), темнота и логистика делают исследование океана сложнее, чем Марса."
    },
]

QUIZZES_MAP = {
    "queue5": QUIZZES_Q5,
    "queue3": QUIZZES_Q3,
    "queue4": QUIZZES_Q4,
    "queue2": [],  # для исторического канала не делаем
}

async def get_last_scheduled_date(client, entity):
    """Получает дату последнего запланированного поста."""
    from telethon.tl.functions.messages import GetScheduledHistoryRequest
    try:
        result = await client(GetScheduledHistoryRequest(peer=entity, hash=0))
        if result.messages:
            dates = [m.date for m in result.messages if hasattr(m, 'date')]
            return max(dates) if dates else None
    except Exception:
        pass
    return None

def schedule_quiz_bot_api(bot_token, chat_id, quiz, schedule_date):
    """Планирует quiz-опрос через Bot API (надёжнее MTProto для опросов)."""
    import urllib.request, ssl
    url = f"https://api.telegram.org/bot{bot_token}/sendPoll"
    ctx = ssl.create_default_context()
    # Bot API: explanation max 200 chars
    explanation = quiz["explanation"][:200]
    data = json.dumps({
        "chat_id": chat_id,
        "question": quiz["question"][:300],
        "options": [{"text": o[:100]} for o in quiz["options"]],
        "type": "quiz",
        "correct_option_id": quiz["correct"],
        "explanation": explanation,
        "is_anonymous": True,
        "schedule_date": int(schedule_date.timestamp()),
    }).encode()
    req = urllib.request.Request(url, data=data,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
            resp = json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}")
    if not resp.get("ok"):
        raise RuntimeError(resp.get("description", str(resp)))
    return resp

async def main():
    queue = sys.argv[1] if len(sys.argv) > 1 else "queue5"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    if queue not in CHANNELS:
        print(f"Неизвестная очередь: {queue}"); return
    if queue not in QUIZZES_MAP or not QUIZZES_MAP[queue]:
        print(f"Нет викторин для {queue}"); return

    channel  = CHANNELS[queue]
    quizzes  = QUIZZES_MAP[queue]
    count    = min(count, len(quizzes))

    bot_token = cfg.get("bot_token", "")

    from telethon import TelegramClient
    client = TelegramClient(SESSION, int(API_ID), API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Не авторизован"); return

    entity = await client.get_entity(channel)

    # Находим дату последнего запланированного поста
    last_date = await get_last_scheduled_date(client, entity)
    await client.disconnect()

    if last_date:
        base_date = last_date + timedelta(hours=4)
    else:
        base_date = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0) + timedelta(days=1)

    print(f"\n=== Добавляем {count} quiz-опросов в {channel} ===")
    print(f"  Первый после: {base_date.strftime('%d.%m.%Y %H:%M')} UTC\n")

    selected = random.sample(quizzes, count)
    import time

    success = 0
    for i, quiz in enumerate(selected):
        schedule_date = base_date + timedelta(hours=i * 4)
        print(f"[{i+1}/{count}] 📅 {schedule_date.strftime('%d.%m %H:%M')} UTC")
        print(f"  ❓ {quiz['question'][:60]}...")

        try:
            schedule_quiz_bot_api(bot_token, channel, quiz, schedule_date)
            print(f"  ✅ Запланировано!")
            success += 1
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")

        time.sleep(1)

    print(f"\n✅ Готово! Добавлено {success}/{count} викторин в {channel}")

if __name__ == "__main__":
    asyncio.run(main())
