#!/usr/bin/env python3
"""
auto_publish.py — реальное планирование постов в Telegram через Telethon (личный аккаунт).

ВАЖНО: Bot API НЕ поддерживает schedule_date — параметр игнорируется и пост
публикуется немедленно. Поэтому здесь используется Telethon (MTProto), который
поддерживает настоящее серверное планирование (client.send_message(..., schedule=dt)).
Telegram сам хранит отложенный пост и публикует его точно по времени — Мак
не обязан быть включён в момент публикации, только в момент ПОСТАНОВКИ в очередь.

Что делает:
1. Читает queue/*.json напрямую из GitHub (через API)
2. Для каждого поста без картинки — ищет на Wikipedia по полю wiki_article
3. СТАВИТ пост в расписание Telegram (schedule=) — не публикует сразу
4. Удаляет файл из queue/ на GitHub после успешной постановки в расписание
5. Сохраняет analytics/{message_id}.json на GitHub для статистики

ПРЕДОХРАНИТЕЛЬ: не более MAX_PER_RUN постов за один запуск — чтобы повторение
истории с флудом было физически невозможно даже при будущих багах.
"""

import asyncio, json, os, ssl, time, base64, sys, io
import urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

from telethon import TelegramClient
from telethon.tl.functions.messages import GetScheduledHistoryRequest

BASE       = os.path.dirname(os.path.abspath(__file__))
CONFIG     = os.path.join(BASE, "config.json")
SESSION    = os.path.join(BASE, "tg_user_session")
LOG_PATH   = os.path.join(BASE, "auto_publish.log")

API_ID     = 39578814
API_HASH   = "18f9ab304c0119a6ab28ff913f02f192"

RIGA_TZ    = timezone(timedelta(hours=3))
POST_HOURS = [7, 11, 13, 16, 18, 22]

MAX_PER_RUN = 6   # предохранитель: не больше 6 постов поставить в расписание за один запуск

import logging
logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format="%(asctime)s %(message)s")

def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def fetch(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "HistoryBot/1.0"})
    with urllib.request.urlopen(req, timeout=10, context=ssl_ctx()) as r:
        return json.loads(r.read())

def fetch_image_for_telegram(url):
    # БАГ-ФИКС (22.06, жалоба "картинка прикреплена как файл, а не как фото"): Telethon
    # решает фото-или-документ по РАСШИРЕНИЮ имени файла в URL/строке — а ссылки на
    # AI-картинки (Pollinations, используются для facts-каналов) выглядят как
    # ".../prompt/...?width=800&seed=123&nologo=true" БЕЗ .jpg/.png на конце. Без
    # расширения Telethon не узнаёт в этом фото и шлёт как обычный файл-документ.
    # Качаем картинку сами и оборачиваем в BytesIO с явным .jpg-именем — тогда
    # Telethon видит расширение и отправляет как нормальное сжатое фото.
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20, context=ssl_ctx()) as r:
            data = r.read()
        buf = io.BytesIO(data)
        buf.name = "photo.jpg"
        return buf
    except Exception as e:
        logging.warning(f"Не смог скачать картинку для отправки как фото ({url[:80]}): {e} — отправлю по URL как раньше")
        return url

def get_thumbnail(article: str) -> str:
    data = fetch("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "titles": article,
        "prop": "pageimages", "pithumbsize": 800, "format": "json"
    }))
    for page in data["query"]["pages"].values():
        src = page.get("thumbnail", {}).get("source", "")
        if src:
            return src
    return ""

def make_slots(n: int, taken: set) -> list:
    """Генерирует n будущих слотов, пропуская уже занятые (taken — set unix timestamps)."""
    now = datetime.now(RIGA_TZ)
    slots, day = [], now.date()
    while len(slots) < n:
        for h in POST_HOURS:
            dt = datetime(day.year, day.month, day.day, h, 0, 0, tzinfo=RIGA_TZ)
            ts = int(dt.timestamp())
            if dt > now + timedelta(minutes=10) and ts not in taken:
                slots.append(ts)
                taken.add(ts)
                if len(slots) == n:
                    break
        day += timedelta(days=1)
    return slots

# ── GitHub API ──────────────────────────────────────────────────────────────
def gh_headers(gh_token):
    return {"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"}

def gh_list_queue(gh_token, gh_repo, queue_dir="queue"):
    url = f"https://api.github.com/repos/{gh_repo}/contents/{queue_dir}"
    req = urllib.request.Request(url, headers=gh_headers(gh_token))
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
            items = json.loads(r.read())
    except Exception as e:
        logging.error(f"gh_list_queue ошибка ({queue_dir}): {e}")
        return []
    return sorted([it for it in items if it["type"] == "file" and it["name"].endswith(".json")],
                  key=lambda it: it["name"])

def gh_get_file(gh_repo, path, gh_token):
    url = f"https://api.github.com/repos/{gh_repo}/contents/{path}"
    req = urllib.request.Request(url, headers=gh_headers(gh_token))
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        data = json.loads(r.read())
    content = json.loads(base64.b64decode(data["content"]).decode("utf-8"))
    return content, data["sha"]

def gh_put_file(gh_repo, path, obj, sha, gh_token, msg):
    url = f"https://api.github.com/repos/{gh_repo}/contents/{path}"
    payload = {
        "message": msg,
        "content": base64.b64encode(json.dumps(obj, ensure_ascii=False, indent=2).encode()).decode(),
    }
    if sha:
        payload["sha"] = sha
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="PUT", headers={**gh_headers(gh_token), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())

def gh_delete_file(gh_repo, path, sha, gh_token, msg):
    url = f"https://api.github.com/repos/{gh_repo}/contents/{path}"
    payload = {"message": msg, "sha": sha}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="DELETE", headers={**gh_headers(gh_token), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())

def gh_delete_file_retry(gh_repo, path, sha, gh_token, msg, attempts=3):
    """Удаление файла из очереди с повтором — раньше один таймаут/409 оставлял файл
    в очереди НАВСЕГДА (до следующего запуска), и тот же уже опубликованный пост
    подхватывался заново и публиковался ВТОРОЙ раз (баг "пост раздвоился"). При 409
    (sha разошлась — кто-то параллельно поменял файл, например мини-апп) перечитываем
    актуальный sha с GitHub и пробуем удалить ещё раз этим sha."""
    last_err = None
    for attempt in range(attempts):
        try:
            return gh_delete_file(gh_repo, path, sha, gh_token, msg)
        except Exception as e:
            last_err = e
            if "404" in str(e):
                return None  # уже удалён (например, предыдущей попыткой) — не ошибка
            if "409" in str(e):
                try:
                    url = f"https://api.github.com/repos/{gh_repo}/contents/{path}"
                    req = urllib.request.Request(url, headers=gh_headers(gh_token))
                    with urllib.request.urlopen(req, timeout=10, context=ssl_ctx()) as r:
                        sha = json.loads(r.read())["sha"]
                except Exception:
                    pass
            if attempt < attempts - 1:
                time.sleep(3)
    raise last_err

def gh_put_analytics(path, obj, gh_token, gh_repo, msg):
    url = f"https://api.github.com/repos/{gh_repo}/contents/{path}"
    sha = None
    try:
        req = urllib.request.Request(url, headers=gh_headers(gh_token))
        with urllib.request.urlopen(req, timeout=10, context=ssl_ctx()) as r:
            sha = json.loads(r.read()).get("sha")
    except Exception:
        pass
    payload = {
        "message": msg,
        "content": base64.b64encode(json.dumps(obj, ensure_ascii=False, indent=2).encode()).decode()
    }
    if sha:
        payload["sha"] = sha
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="PUT", headers={**gh_headers(gh_token), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())


async def process_channel(client, gh_token, gh_repo, channel, queue_dir, analytics_dir, dry_run=False):
    print(f"\n=== Канал {channel} (папка {queue_dir}/) ===")
    try:
        entity = await client.get_entity(channel)
    except Exception as e:
        print(f"❌ не смог получить канал {channel}: {e} (проверь что аккаунт админ там)")
        logging.error(f"get_entity {channel}: {e}")
        return

    # КРИТИЧЕСКИЙ ФИКС "2 поста в одну минуту" / дубли: скрипт запускается каждые 30 минут
    # через launchd, и раньше "занятые" слоты (taken) считались ТОЛЬКО из ручных scheduled_at
    # постов, ОСТАВШИХСЯ в очереди GitHub. Авто-слоты, занятые ПРЕДЫДУЩИМ запуском, никуда
    # не сохранялись локально — как только пост успешно поставлен в Telegram, его файл
    # удаляется из очереди, и при следующем запуске make_slots() заново строит "пустое"
    # расписание, ничего не зная о только что использованном времени → выбирает ТО ЖЕ самое
    # время для другого поста → два разных поста в один и тот же слот. Источник истины —
    # сам Telegram (что реально УЖЕ поставлено в его расписании), не локальный файл, поэтому
    # запрашиваем это напрямую перед расчётом слотов. Это же defensive-снимок используем для
    # дедупликации текста: если до этого gh_delete_file не сработал (таймаут/409 — такое
    # бывало в логах) и файл остался в очереди, follow-up запуск попытался бы запостить
    # ТОТ ЖЕ текст ещё раз — выглядит как "один пост раздвоился".
    # БАГ-ФИКС (найден 22.06 — посты дублировались на одно и то же время несмотря на
    # предыдущий "фикс"): client.get_messages(entity, scheduled=True) — это высокоуровневая
    # обёртка Telethon, которая в этом окружении НЕНАДЁЖНО недосчитывает реально запланированные
    # сообщения (та же проблема уже была обнаружена и обойдена в dedupe_schedule.py через сырой
    # API-запрос). Из-за недосчёта existing_times/existing_texts были неполными — make_slots()
    # считал часы "свободными", хотя Telegram уже хранил там пост, и при следующих запусках
    # (каждые 30 мин) создавались НОВЫЕ сообщения на ТО ЖЕ время (видно в логах: 24.06 18:00
    # создавался 3 раза подряд с разными message_id). Переходим на сырой
    # GetScheduledHistoryRequest(hash=0) — именно он надёжно отдаёт полный список.
    existing_times, existing_texts = set(), set()
    try:
        raw_scheduled = await client(GetScheduledHistoryRequest(peer=entity, hash=0))
        existing_scheduled = [m for m in raw_scheduled.messages if hasattr(m, "date") and hasattr(m, "id")]
        for m in existing_scheduled:
            if getattr(m, "date", None):
                existing_times.add(int(m.date.timestamp()))
            body = (getattr(m, "message", None) or "").strip()
            if body:
                existing_texts.add(body)
        print(f"  ℹ️ уже в расписании Telegram (raw API): {len(existing_scheduled)} постов")

        # БАГ-ФИКС "в миниапп список постов почти пуст, хотя в Telegram расписание полное"
        # (жалоба про канал 2: в Telegram 50+ постов на недели вперёд, а в миниапп список
        # показывал только 1-2 — реальный гэп казался катастрофой). Причина: миниапп строит
        # список ИСКЛЮЧИТЕЛЬНО из очереди GitHub (queue/queue2) — как только этот скрипт
        # успешно ставит пост в расписание Telegram, файл удаляется из очереди (это правильно
        # и ожидаемо), но миниапп тогда вообще не видит, что пост всё ещё "впереди", просто
        # уже не в GitHub, а напрямую в Telegram. Пишем снимок реального расписания обратно
        # в GitHub при каждом запуске — миниапп подмешивает его в список (см. index.html
        # loadScheduleSnapshot), не теряя из виду уже-переданные-в-Telegram посты.
        try:
            # БАГ-ФИКС "в миниапп нельзя посмотреть картинку у уже запланированных постов":
            # сначала снимок хранил только id/время/текст — миниапп открывал такую запись
            # без фото. Картинка, с которой пост реально был поставлен в Telegram, уже
            # сохранена в analytics/{id}.json (см. запись record["image_url"] чуть ниже по
            # файлу, в месте отправки) — подтягиваем её сюда же, чтобы превью совпадало
            # с тем, что реально увидят подписчики.
            snapshot = []
            for m in existing_scheduled:
                image_url = None
                try:
                    rec, _ = gh_get_file(gh_repo, f"{analytics_dir}/{m.id}.json", gh_token)
                    image_url = rec.get("image_url")
                except Exception:
                    pass
                snapshot.append({
                    "id": m.id,
                    "scheduled_at": m.date.isoformat(),
                    "text": (getattr(m, "message", None) or "").strip()[:500],
                    "image_url": image_url,
                })
            snapshot.sort(key=lambda x: x["scheduled_at"])
            gh_put_analytics(f"{queue_dir}_schedule_snapshot.json", snapshot, gh_token, gh_repo,
                              f"Snapshot реального расписания {queue_dir}")
            print(f"  📸 снимок расписания сохранён ({len(snapshot)} постов, с картинками: {sum(1 for s in snapshot if s['image_url'])})")
        except Exception as e:
            print(f"  ⚠️ не смог сохранить снимок расписания: {e}")
            logging.warning(f"schedule snapshot save failed for {queue_dir}: {e}")
    except Exception as e:
        print(f"  ⚠️ не смог получить уже запланированные посты Telegram: {e} (риск дублей/коллизий слотов)")
        logging.warning(f"GetScheduledHistoryRequest {channel}: {e}")

    items = gh_list_queue(gh_token, gh_repo, queue_dir)
    if not items:
        logging.info(f"Очередь пуста ({queue_dir})")
        print("Очередь пуста.")
        return

    print(f"Постов в очереди (GitHub): {len(items)}")
    logging.info(f"Старт {queue_dir}: {len(items)} постов в очереди")

    loaded = []
    for it in items:
        try:
            post, sha = gh_get_file(gh_repo, it["path"], gh_token)
            loaded.append((it, post, sha))
        except Exception as e:
            print(f"  ❌ не смог прочитать {it['name']}: {e}")
            logging.error(f"gh_get_file {it['name']}: {e}")

    # БАГ-ФИКС "посты на субботу/воскресенье висят в списке хотя уже понедельник":
    # gh_list_queue() сортирует файлы по ИМЕНИ (нужно для стабильности при параллельной
    # записи), а имена — смесь старых "001.json"/"20260621_...json" и новых
    # "slot-YYYY-MM-DDTHH.json". При очереди в 100+ постов и лимите MAX_PER_RUN=6 за
    # запуск публикующийся ПОРЯДОК = алфавитный порядок имён, а НЕ порядок реальной
    # срочности (scheduled_at) — пост с уже прошедшей датой может алфавитно оказаться
    # в конце списка и физически не доходить до публикации много запусков подряд, пока
    # другие, более новые по дате, но алфавитно более ранние посты обрабатываются раньше.
    # Сортируем: сначала посты с ручным scheduled_at (от самого просроченного/раннего),
    # затем все остальные — в их прежнем относительном порядке (стабильная сортировка).
    def _urgency_key(loaded_item):
        _, post, _ = loaded_item
        sa = post.get("scheduled_at")
        if sa:
            try:
                ts = datetime.fromisoformat(sa.replace("Z", "+00:00")).timestamp()
                return (0, ts)
            except Exception:
                pass
        return (1, 0)
    loaded.sort(key=_urgency_key)

    # Шаг 1: картинки
    print("\n── Добавляю картинки ──")
    for it, post, sha in loaded:
        if post.get("image_url") or not post.get("wiki_article"):
            continue
        article = post["wiki_article"]
        print(f"  {it['name']} «{article}»", end=" ... ", flush=True)
        for attempt in range(3):
            try:
                url = get_thumbnail(article)
                if url:
                    post["image_url"] = url
                    if not dry_run:
                        res = gh_put_file(gh_repo, it["path"], post, sha, gh_token, f"Add image: {it['name']}")
                        sha = res.get("content", {}).get("sha", sha)
                    print("✅")
                else:
                    print("⚠️ нет фото")
                break
            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    time.sleep(8)
                else:
                    print(f"❌ {e}")
                    break
        time.sleep(0.5)

    # Собираем уже занятые слоты (ручные scheduled_at в будущем + реально занятые в Telegram
    # слоты из existing_times выше) — чтобы авто-слоты их не перекрывали
    now_ts = int(datetime.now(RIGA_TZ).timestamp())
    taken = set(existing_times)
    for _, post, _ in loaded:
        if post.get("scheduled_at"):
            try:
                t = int(datetime.fromisoformat(post["scheduled_at"].replace("Z", "+00:00")).timestamp())
                if t > now_ts:
                    taken.add(t)
            except Exception:
                pass

    # БАГ-ФИКС: раньше размер пула авто-слотов считался ТОЛЬКО по постам без
    # scheduled_at вообще. Посты с ПРОСРОЧЕННЫМ scheduled_at (ручная дата уже прошла,
    # пост не успел уйти) тоже падают в авто-присвоение чуть ниже, но не учитывались
    # в размере пула — при достаточно большом заторе они конкурировали за те же
    # несколько слотов и часть навсегда оставалась без слота (continue, пропуск) даже
    # при наличии запаса в MAX_PER_RUN. Считаем оба случая.
    def _needs_auto_slot(post):
        sa = post.get("scheduled_at")
        if not sa:
            return True
        try:
            t = int(datetime.fromisoformat(sa.replace("Z", "+00:00")).timestamp())
            return t <= now_ts + 60
        except Exception:
            return True
    auto_slots_needed = sum(1 for _, post, _ in loaded if _needs_auto_slot(post))
    auto_slots = make_slots(max(auto_slots_needed, 1), taken) if auto_slots_needed else []
    auto_idx = 0

    # claimed_times — живое множество "уже занято в ЭТОМ запуске", растёт по ходу публикации.
    # Отдельно от taken (который зафиксирован один раз для расчёта пула auto_slots) — нужно
    # ловить коллизии МЕЖДУ ручными slot'ами в реальном времени, пост за постом.
    claimed_times = set(existing_times)

    print(f"\n── Ставлю в расписание Telegram (максимум {MAX_PER_RUN} за запуск) ──")
    ok = fail = 0

    for it, post, sha in loaded:
        if ok >= MAX_PER_RUN:
            print(f"  ⏸ Достигнут лимит {MAX_PER_RUN} за запуск — остальное в следующий раз")
            break

        text      = (post.get("text") or "").strip()
        image_url = (post.get("image_url") or "").strip()

        if not text:
            if not dry_run:
                try: gh_delete_file_retry(gh_repo, it["path"], sha, gh_token, f"Remove empty: {it['name']}")
                except Exception: pass
            continue

        # Дедуп-страховка против "пост раздвоился": если этот ТОЧНО ТАКОЙ ЖЕ текст уже стоит
        # в расписании Telegram (например предыдущий запуск успешно отправил его, но удаление
        # из очереди GitHub не прошло из-за таймаута/409 — см. лог) — не публикуем повторно,
        # просто чистим файл из очереди как уже обработанный.
        if text in existing_texts:
            print(f"  ⏭ {it['name']} — такой текст уже стоит в расписании Telegram, пропускаю (дубль)")
            logging.warning(f"Skip duplicate already-scheduled text: {it['name']}")
            if not dry_run:
                try: gh_delete_file_retry(gh_repo, it["path"], sha, gh_token, f"Remove duplicate: {it['name']}")
                except Exception: pass
            continue

        # БАГ-ФИКС "несколько постов на одно и то же время" (24.06 18:00 — три разных id):
        # раньше ручной (пинned календарём) scheduled_at брался "как есть", без проверки,
        # что этот ровно этот час уже занят — ни уже существующим постом в Telegram
        # (existing_times), ни ДРУГИМ постом из этой же очереди с тем же явным временем
        # (мини-апп при заполнении календаря мог присвоить двум разным постам один слот).
        # Теперь каждый ручной слот проверяется против общего множества claimed_times —
        # если занят, пост сдвигается на следующий свободный час по тому же расписанию,
        # а не публикуется поверх уже занятого слота.
        ts = None
        manual_ts = None
        if post.get("scheduled_at"):
            try:
                candidate = int(datetime.fromisoformat(post["scheduled_at"].replace("Z", "+00:00")).timestamp())
                if candidate > now_ts + 60:
                    manual_ts = candidate
            except Exception:
                pass

        if manual_ts is not None:
            if manual_ts not in claimed_times:
                ts = manual_ts
                claimed_times.add(ts)
            else:
                fresh = make_slots(1, claimed_times)
                ts = fresh[0]
                claimed_times.add(ts)
                print(f"  ⚠️ {it['name']}: слот {datetime.fromtimestamp(manual_ts, tz=RIGA_TZ).strftime('%d.%m %H:%M')} уже занят — переношу на {datetime.fromtimestamp(ts, tz=RIGA_TZ).strftime('%d.%m %H:%M')}")
                logging.warning(f"{it['name']}: manual slot collision, moved {manual_ts} -> {ts}")
        if ts is None:
            if auto_idx < len(auto_slots):
                ts = auto_slots[auto_idx]
                auto_idx += 1
                claimed_times.add(ts)
            else:
                continue

        schedule_dt = datetime.fromtimestamp(ts, tz=RIGA_TZ)
        dt_str = schedule_dt.strftime("%d.%m %H:%M")

        if dry_run:
            print(f"  [DRY] would schedule {dt_str} — {text[:50]}...")
            continue

        try:
            if image_url:
                photo_file = fetch_image_for_telegram(image_url)
                msg = await client.send_file(entity, file=photo_file, caption=text, schedule=schedule_dt, parse_mode="html", force_document=False)
            else:
                msg = await client.send_message(entity, text, schedule=schedule_dt, parse_mode="html")

            msg_id = msg.id
            existing_texts.add(text)  # чтобы тот же текст не отправился второй раз ВНУТРИ этого же запуска
            print(f"  ✅ {dt_str} — {text[:50]}... (id={msg_id})")
            logging.info(f"Запланировано {dt_str}: {text[:50]} (id={msg_id})")

            record = {
                "message_id": msg_id,
                "text": text,
                "image_url": image_url or None,
                "scheduled_at": schedule_dt.isoformat(),
                "hour": schedule_dt.hour,
                "channel": channel,
                "total_reactions": 0,
                "views_15min": None,
                "ai_generated": post.get("ai_generated", False),
                "ai_tag": post.get("ai_tag"),
                "ai_topic": post.get("ai_topic"),
                "created_at": datetime.now(RIGA_TZ).isoformat(),
            }
            try:
                gh_put_analytics(f"{analytics_dir}/{msg_id}.json", record, gh_token, gh_repo, f"Analytics: msg {msg_id}")
                print(f"     📊 {analytics_dir}/{msg_id}.json сохранён")
            except Exception as e:
                print(f"     ⚠️ не смог сохранить analytics: {e}")
                logging.warning(f"analytics save failed for {msg_id}: {e}")

            try:
                gh_delete_file_retry(gh_repo, it["path"], sha, gh_token, f"Scheduled: {it['name']}")
            except Exception as e:
                print(f"     ⚠️ не смог удалить из очереди после {3} попыток: {e} (на следующем запуске сработает дедуп по тексту)")
                logging.warning(f"gh_delete_file {it['name']}: {e}")

            ok += 1
            await asyncio.sleep(2)  # пауза после успешной отправки — не провоцируем flood-wait
        except Exception as e:
            err_str = str(e)
            print(f"  ❌ {e}")
            logging.error(f"Ошибка для {it['name']}: {e}")
            fail += 1
            # Достигнут лимит 100 отложенных постов Telegram — дальнейшие попытки бесполезны
            if "cannot schedule more messages" in err_str.lower():
                print(f"  ⛔ Лимит 100 отложенных постов — прерываю этот канал")
                break

    print(f"\nГотово ({queue_dir}): {ok} поставлено в расписание, {fail} ошибок.")
    logging.info(f"Финиш {queue_dir}: {ok} поставлено, {fail} ошибок.")


async def main(dry_run=False):
    with open(CONFIG) as f:
        cfg = json.load(f)
    gh_token = cfg.get("github_token", "")
    gh_repo  = cfg.get("github_repo", "ivanmartynov97/telegram-posts")

    # Поддержка нескольких каналов: список "channels" в config.json (канал + своя папка
    # очереди/аналитики). Если списка нет — работаем по-старому с одним channel_id/queue/analytics,
    # чтобы не сломать совместимость для тех, кто не настраивал второй канал.
    channels = cfg.get("channels") or [
        {"channel_id": cfg["channel_id"], "queue_dir": "queue", "analytics_dir": "analytics"}
    ]

    if not gh_token:
        print("❌ github_token не задан в config.json")
        logging.error("github_token не задан")
        return

    if not os.path.exists(SESSION + ".session"):
        print("❌ Telethon сессия не найдена. Запусти auth_phone.command")
        return

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Сессия не авторизована. Запусти auth_phone.command")
        await client.disconnect()
        return

    me = await client.get_me()
    print(f"✅ Авторизован как {me.first_name} (@{me.username})")

    for ch in channels:
        try:
            await process_channel(client, gh_token, gh_repo, ch["channel_id"],
                                   ch.get("queue_dir", "queue"), ch.get("analytics_dir", "analytics"),
                                   dry_run=dry_run)
        except Exception as e:
            print(f"❌ Ошибка обработки канала {ch.get('channel_id')}: {e}")
            logging.error(f"process_channel {ch.get('channel_id')}: {e}")

    await client.disconnect()

if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    asyncio.run(main(dry_run=dry))
