#!/usr/bin/env python3
"""
analyze_channels.py — анализ контента конкурентов/вдохновения.

Что делает:
- Читает последние N постов из указанных каналов
- Собирает: текст, просмотры, реакции, длину, наличие фото, время
- Считает engagement_rate для каждого поста
- Группирует по темам и форматам
- Сохраняет в analytics/competitors.json
- Выводит топ-5 лучших постов и тренды

Запуск: python3 analyze_channels.py
"""

import asyncio, json, os, re, ssl, base64, logging
import urllib.request
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest

BASE    = os.path.dirname(os.path.abspath(__file__))
CONFIG  = os.path.join(BASE, "config.json")
SESSION = os.path.join(BASE, "tg_user_session")
LOG     = os.path.join(BASE, "analyze_channels.log")

API_ID   = 39578814
API_HASH = "18f9ab304c0119a6ab28ff913f02f192"

# ── Каналы для анализа ────────────────────────────────────────────────────────
# Добавь сюда каналы которые хочешь анализировать
CHANNELS_TO_ANALYZE = [
    "@historyofrussia",
    "@history_channel",
    "@historyfacts_channel",
    # добавляй свои:
]
POSTS_PER_CHANNEL = 50  # последних постов

logging.basicConfig(filename=LOG, level=logging.INFO, format="%(asctime)s %(message)s")

def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    return ctx

def gh_put(path, content_str, sha, msg, gh_token):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    content = base64.b64encode(content_str.encode()).decode()
    payload = {"message": msg, "content": content}
    if sha: payload["sha"] = sha
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="PUT",
          headers={"Authorization": f"token {gh_token}",
                   "Accept": "application/vnd.github.v3+json",
                   "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())

def gh_get_file(path, gh_token):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    req = urllib.request.Request(url,
          headers={"Authorization": f"token {gh_token}",
                   "Accept": "application/vnd.github.v3+json"})
    try:
        with urllib.request.urlopen(req, timeout=10, context=ssl_ctx()) as r:
            data = json.loads(r.read())
            return json.loads(base64.b64decode(data["content"].replace("\n","")).decode()), data["sha"]
    except Exception:
        return {}, None

def extract_topics(text):
    """Извлекает темы из текста поста."""
    if not text: return []
    years = re.findall(r"\b(1[5-9]\d{2}|20[0-2]\d)\b", text)
    caps = re.findall(r"[А-ЯЁA-Z][а-яёa-z]{3,}", text)
    caps = [w for w in caps if w not in {"Это","Его","Она","Они","Когда","Если","Также"}]
    return list(dict.fromkeys(caps[:2] + years[:1]))[:3]

def post_format(text, has_photo):
    """Определяет формат поста."""
    if not text: return "photo_only"
    length = len(text)
    if has_photo and length < 200: return "photo_caption"
    if has_photo: return "photo_text"
    if length < 150: return "short"
    if length > 600: return "long"
    return "medium"

def analyze_posts(posts_data):
    """Агрегирует статистику по топикам и форматам."""
    topics_stat = {}
    formats_stat = {}
    top_posts = sorted(posts_data, key=lambda p: p.get("engagement_rate", 0), reverse=True)[:10]

    for p in posts_data:
        # По форматам
        fmt = p.get("format", "unknown")
        if fmt not in formats_stat:
            formats_stat[fmt] = {"count": 0, "total_rate": 0, "avg_rate": 0}
        formats_stat[fmt]["count"] += 1
        formats_stat[fmt]["total_rate"] += p.get("engagement_rate", 0)

        # По темам
        for topic in p.get("topics", []):
            if topic not in topics_stat:
                topics_stat[topic] = {"count": 0, "total_rate": 0, "avg_rate": 0, "best_rate": 0}
            topics_stat[topic]["count"] += 1
            topics_stat[topic]["total_rate"] += p.get("engagement_rate", 0)
            if p.get("engagement_rate", 0) > topics_stat[topic]["best_rate"]:
                topics_stat[topic]["best_rate"] = p["engagement_rate"]

    for v in formats_stat.values():
        if v["count"]: v["avg_rate"] = round(v["total_rate"] / v["count"], 2)
    for v in topics_stat.values():
        if v["count"]: v["avg_rate"] = round(v["total_rate"] / v["count"], 2)

    return topics_stat, formats_stat, top_posts

async def main():
    with open(CONFIG) as f: cfg = json.load(f)
    gh_token = cfg.get("github_token", "")
    global GH_REPO
    GH_REPO = "ivanmartynov97/telegram-posts"

    if not os.path.exists(SESSION + ".session"):
        print("❌ Сессия Telethon не найдена. Запусти qr_login.command")
        return

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print("❌ Не авторизован. Запусти qr_login.command")
        await client.disconnect()
        return

    all_posts = []
    results_by_channel = {}

    for channel_name in CHANNELS_TO_ANALYZE:
        print(f"\n📊 Анализирую {channel_name}...")
        try:
            entity = await client.get_entity(channel_name)
            full   = await client(GetFullChannelRequest(entity))
            subscribers = full.full_chat.participants_count
            print(f"   Подписчиков: {subscribers:,}")

            messages = await client.get_messages(entity, limit=POSTS_PER_CHANNEL)
            channel_posts = []

            for msg in messages:
                if not msg or not msg.id: continue
                text = getattr(msg, "text", "") or getattr(msg, "caption", "") or ""
                views = getattr(msg, "views", 0) or 0
                has_photo = bool(getattr(msg, "photo", None) or getattr(msg, "media", None))

                # Реакции
                total_reactions = 0
                reactions_dict = {}
                if getattr(msg, "reactions", None):
                    for r in msg.reactions.results:
                        emoji = getattr(r.reaction, "emoticon", "?")
                        reactions_dict[emoji] = r.count
                        total_reactions += r.count

                # Forwarded count
                fwd_count = getattr(msg, "forwards", 0) or 0

                pub_time = msg.date.astimezone(timezone(timedelta(hours=3)))
                hours_old = (datetime.now(timezone(timedelta(hours=3))) - pub_time).total_seconds() / 3600

                # Engagement rate = (views + reactions*5 + fwd*10) / subscribers * 1000
                engagement = views + total_reactions * 5 + fwd_count * 10
                rate = round(engagement / max(subscribers, 1) * 1000, 2) if subscribers else 0

                post = {
                    "channel": channel_name,
                    "message_id": msg.id,
                    "text_preview": text[:200],
                    "char_count": len(text),
                    "has_photo": has_photo,
                    "views": views,
                    "reactions": total_reactions,
                    "reactions_breakdown": reactions_dict,
                    "forwards": fwd_count,
                    "engagement_rate": rate,
                    "format": post_format(text, has_photo),
                    "topics": extract_topics(text),
                    "published_at": pub_time.isoformat(),
                    "hours_old": round(hours_old, 1),
                }
                channel_posts.append(post)
                all_posts.append(post)

            topics_stat, formats_stat, top = analyze_posts(channel_posts)

            results_by_channel[channel_name] = {
                "subscribers": subscribers,
                "posts_analyzed": len(channel_posts),
                "avg_views": round(sum(p["views"] for p in channel_posts) / max(len(channel_posts), 1)),
                "avg_reactions": round(sum(p["reactions"] for p in channel_posts) / max(len(channel_posts), 1), 1),
                "top_formats": dict(sorted(formats_stat.items(), key=lambda x: x[1]["avg_rate"], reverse=True)[:3]),
                "top_topics": dict(sorted(topics_stat.items(), key=lambda x: x[1]["avg_rate"], reverse=True)[:10]),
                "top_posts": top,
            }

            # Печатаем топ-3
            print(f"   Топ форматы: {', '.join(list(formats_stat.keys())[:3])}")
            print(f"   Топ пост: {top[0]['text_preview'][:80]}..." if top else "")

        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            logging.warning(f"Channel {channel_name}: {e}")

    # Общая сводка по всем каналам
    if all_posts:
        all_topics, all_formats, global_top = analyze_posts(all_posts)
        summary = {
            "analyzed_at": datetime.now(timezone(timedelta(hours=3))).isoformat(),
            "channels": list(CHANNELS_TO_ANALYZE),
            "total_posts": len(all_posts),
            "global_top_topics": dict(sorted(all_topics.items(), key=lambda x: x[1]["avg_rate"], reverse=True)[:15]),
            "global_top_formats": all_formats,
            "global_top_posts": global_top[:5],
            "by_channel": results_by_channel,
        }

        # Сохраняем в GitHub
        existing, sha = gh_get_file("analytics/competitors.json", gh_token)
        content_str = json.dumps(summary, ensure_ascii=False, indent=2)
        if gh_token:
            gh_put("analytics/competitors.json", content_str, sha,
                   f"Competitor analysis: {len(all_posts)} posts", gh_token)
            print(f"\n✅ Сохранено в analytics/competitors.json ({len(all_posts)} постов)")

        # Красивый вывод
        print("\n" + "="*50)
        print("🏆 ТОП ТЕМЫ (лучший engagement rate):")
        for topic, stat in sorted(all_topics.items(), key=lambda x: x[1]["avg_rate"], reverse=True)[:8]:
            print(f"   {topic}: avg={stat['avg_rate']} (постов: {stat['count']})")

        print("\n📋 ЛУЧШИЕ ФОРМАТЫ:")
        for fmt, stat in sorted(all_formats.items(), key=lambda x: x[1]["avg_rate"], reverse=True):
            print(f"   {fmt}: avg={stat['avg_rate']} (постов: {stat['count']})")

        print("\n🔥 ТОП-3 ПОСТА:")
        for i, p in enumerate(global_top[:3], 1):
            print(f"\n{i}. [{p['channel']}] views={p['views']} rate={p['engagement_rate']}")
            print(f"   {p['text_preview'][:120]}...")

    await client.disconnect()

asyncio.run(main())
