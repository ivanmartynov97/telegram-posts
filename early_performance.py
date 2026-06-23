#!/usr/bin/env python3
"""
early_performance.py — анализ охватов за первые 15 минут.

Запускается каждые 5 минут (launchd).
Находит посты опубликованные 10–25 минут назад.
Считает early_engagement_rate = views_15min / subscribers * 1000 (на 1000 подписчиков).
Сохраняет в analytics/{message_id}.json и обновляет analytics/topic_performance.json.

Установка:
  pip3 install telethon
  python3 setup_telethon.py   # один раз — авторизация
  cp com.ivan.early-performance.plist ~/Library/LaunchAgents/
  launchctl load ~/Library/LaunchAgents/com.ivan.early-performance.plist
"""

import asyncio, json, os, ssl, base64, re, logging
import urllib.request
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest

BASE        = os.path.dirname(os.path.abspath(__file__))
CONFIG      = os.path.join(BASE, "config.json")
SESSION     = os.path.join(BASE, "tg_user_session")
LOG_PATH    = os.path.join(BASE, "early_performance.log")
GH_REPO     = "ivanmartynov97/telegram-posts"

# Окно для early snapshot (минуты)
EARLY_MIN   = 10
EARLY_MAX   = 25

logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format="%(asctime)s %(message)s")


# ── helpers ──────────────────────────────────────────────────────────────────

def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def gh_request(method, path, gh_token, payload=None):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method,
          headers={"Authorization": f"token {gh_token}",
                   "Accept": "application/vnd.github.v3+json",
                   "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())

def gh_get(path, gh_token):
    return gh_request("GET", path, gh_token)

def gh_put(path, content_str, sha, msg, gh_token):
    content = base64.b64encode(content_str.encode("utf-8")).decode()
    payload = {"message": msg, "content": content}
    if sha:
        payload["sha"] = sha
    return gh_request("PUT", path, gh_token, payload)

def gh_create(path, content_str, msg, gh_token):
    content = base64.b64encode(content_str.encode("utf-8")).decode()
    return gh_request("PUT", path, gh_token, {"message": msg, "content": content})

def load_analytics_record(mid, gh_token):
    """Загружает одну запись analytics/{mid}.json. Возвращает (record, sha) или (None, None)."""
    try:
        data = gh_get(f"analytics/{mid}.json", gh_token)
        record = json.loads(base64.b64decode(data["content"].replace("\n","")).decode("utf-8"))
        return record, data["sha"]
    except Exception:
        return None, None

def load_json_from_github(path, gh_token):
    """Загружает JSON файл из GitHub. Возвращает (obj, sha) или ({}, None)."""
    try:
        data = gh_get(path, gh_token)
        obj = json.loads(base64.b64decode(data["content"].replace("\n","")).decode("utf-8"))
        return obj, data["sha"]
    except Exception:
        return {}, None


# ── topic extraction ──────────────────────────────────────────────────────────

def extract_topics(text: str) -> list[str]:
    """Вытаскивает ключевые темы из текста поста (proper nouns + years)."""
    if not text:
        return []
    clean = re.sub(r"<[^>]+>", " ", text)
    # Годы
    years = re.findall(r"\b(1[5-9]\d{2}|20[0-2]\d)\b", clean)
    # Имена собственные (русские слова с заглавной буквы, 4+ символов)
    caps = re.findall(r"[А-ЯЁ][а-яё]{3,}", clean)
    # Убираем первое слово (скорее всего начало предложения)
    caps = caps[1:] if len(caps) > 1 else caps
    topics = list(dict.fromkeys(caps[:3] + years[:1]))  # deduplicate, max 4
    return topics[:3]


# ── main ─────────────────────────────────────────────────────────────────────

async def main():
    with open(CONFIG) as f:
        cfg = json.load(f)

    gh_token = cfg.get("github_token", "")
    channel  = cfg.get("channel_id", "")
    api_id   = 39578814
    api_hash = "18f9ab304c0119a6ab28ff913f02f192"

    if not all([gh_token, channel]):
        logging.error("Не заданы github_token / channel_id в config.json")
        return

    if not os.path.exists(SESSION + ".session"):
        logging.error("Сессия Telethon не найдена. Запусти: python3 setup_telethon.py")
        return

    now_riga = datetime.now(timezone(timedelta(hours=3)))
    logging.info(f"=== early_performance start {now_riga.strftime('%H:%M')} ===")

    client = TelegramClient(SESSION, api_id, api_hash)
    await client.connect()
    try:
        # Количество подписчиков
        full = await client(GetFullChannelRequest(channel))
        subscribers = full.full_chat.participants_count
        logging.info(f"Подписчиков: {subscribers}")

        # Последние 30 постов
        messages = await client.get_messages(channel, limit=30)

        processed = 0
        for msg in messages:
            if not msg or not msg.id:
                continue
            pub_time = msg.date.astimezone(timezone(timedelta(hours=3)))
            minutes_old = (now_riga - pub_time).total_seconds() / 60

            # Только посты в окне EARLY_MIN–EARLY_MAX минут
            if not (EARLY_MIN <= minutes_old <= EARLY_MAX):
                continue

            mid      = msg.id
            views    = getattr(msg, "views", 0) or 0
            forwards = getattr(msg, "forwards", 0) or 0

            # Реакции
            reactions_dict = {}
            total_reactions = 0
            if getattr(msg, "reactions", None):
                for r in msg.reactions.results:
                    emoji = getattr(r.reaction, "emoticon", str(r.reaction))
                    reactions_dict[emoji] = r.count
                    total_reactions += r.count

            # Комментарии
            replies = getattr(msg, "replies", None)
            comments = replies.replies if replies else 0

            # early_engagement_rate: views на 1000 подписчиков
            if subscribers > 0:
                early_rate = round(views / subscribers * 1000, 2)
            else:
                early_rate = 0

            text = getattr(msg, "text", "") or getattr(msg, "caption", "") or ""
            topics = extract_topics(text)

            # Загружаем существующую запись из GitHub
            record, sha = load_analytics_record(mid, gh_token)

            if record is None:
                # Создаём новую
                record = {
                    "message_id": mid,
                    "text": text,
                    "published_at": pub_time.isoformat(),
                    "has_image": bool(getattr(msg, "photo", None) or getattr(msg, "media", None)),
                    "char_count": len(text),
                    "topics": topics,
                }

            # Пишем early snapshot только один раз
            if not record.get("early_views"):
                record["early_views"]      = views
                record["early_reactions"]  = total_reactions
                record["early_comments"]   = comments
                record["early_forwards"]   = forwards  # репосты на момент снимка (~15-25 мин)
                record["early_rate"]       = early_rate  # views per 1000 subs at ~15min
                record["early_snapshot_at"] = now_riga.isoformat()
                record["subscribers_at_early"] = subscribers
                record["reactions_breakdown"] = reactions_dict
                record.setdefault("topics", topics)

                content_str = json.dumps(record, ensure_ascii=False, indent=2)
                if sha:
                    gh_put(f"analytics/{mid}.json", content_str, sha,
                           f"Early snapshot: {mid} rate={early_rate}", gh_token)
                else:
                    gh_create(f"analytics/{mid}.json", content_str,
                              f"Early analytics: {mid}", gh_token)

                logging.info(f"msg {mid}: views={views}, rate={early_rate}, topics={topics}")
                print(f"✅ msg {mid}: {views} views, rate={early_rate}/1k subs, topics={topics}")

                # Обновляем сводку по темам
                await update_topic_performance(mid, topics, early_rate, views, text, gh_token)
                processed += 1

        if processed == 0:
            logging.info("Нет постов в окне 10–25 мин")
            print("Нет новых постов для early snapshot")
        else:
            logging.info(f"Обработано: {processed}")

        # Сохраняем количество подписчиков
        await save_subscriber_count(subscribers, gh_token, now_riga)

    finally:
        await client.disconnect()


async def update_topic_performance(mid, topics, early_rate, views, text, gh_token):
    """Обновляет analytics/topic_performance.json — агрегированная статистика по темам."""
    perf, sha = load_json_from_github("analytics/topic_performance.json", gh_token)

    for topic in topics:
        if topic not in perf:
            perf[topic] = {"posts": 0, "total_rate": 0, "best_rate": 0, "best_post_id": None}
        entry = perf[topic]
        entry["posts"] += 1
        entry["total_rate"] += early_rate
        entry["avg_rate"] = round(entry["total_rate"] / entry["posts"], 2)
        if early_rate > entry["best_rate"]:
            entry["best_rate"] = early_rate
            entry["best_post_id"] = mid
        entry["last_updated"] = datetime.now(timezone(timedelta(hours=3))).isoformat()

    content_str = json.dumps(perf, ensure_ascii=False, indent=2)
    if sha:
        gh_put("analytics/topic_performance.json", content_str, sha,
               "Update topic performance", gh_token)
    else:
        gh_create("analytics/topic_performance.json", content_str,
                  "Create topic performance", gh_token)


async def save_subscriber_count(count, gh_token, now):
    """Обновляет analytics/subscriber_history.json — история подписчиков по дням."""
    history, sha = load_json_from_github("analytics/subscriber_history.json", gh_token)
    today = now.strftime("%Y-%m-%d")
    history[today] = {"count": count, "ts": now.isoformat()}
    # Храним 90 дней
    keys = sorted(history.keys())
    if len(keys) > 90:
        for k in keys[:-90]:
            del history[k]
    content_str = json.dumps(history, ensure_ascii=False, indent=2)
    if sha:
        gh_put("analytics/subscriber_history.json", content_str, sha,
               f"Subscribers: {count}", gh_token)
    else:
        gh_create("analytics/subscriber_history.json", content_str,
                  f"Init subscriber history: {count}", gh_token)


asyncio.run(main())
