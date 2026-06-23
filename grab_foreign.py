#!/usr/bin/env python3
"""
grab_foreign.py — берём посты из чужих каналов для переработки.

Что делает:
- Идёт от самого старого поста вперёд по каждому каналу (от даты публикации канала-донора)
- Берёт ЛЮБЫЕ посты (короткие и длинные), кроме рекламных с внешней ссылкой
- Если в посте есть гиперссылка (текст→ссылка) — удаляет слова, в которые она зашита
- Если есть фото — скачивает его и перезаливает в GitHub (foreign/images/), чтобы
  пост можно было использовать с картинкой
- Сохраняет максимум SAVE_PER_RUN новых постов за один запуск (но сканирует
  значительно больше сообщений, чтобы найти подходящие)
- Запоминает позицию в foreign/state.json — следующий запуск продолжит с того же места

Запуск: python3 grab_foreign.py
Или автоматически через grab_foreign.command
"""

import asyncio, json, os, re, ssl, base64, logging, io
import urllib.request
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telethon.tl.types import (
    MessageEntityUrl, MessageEntityTextUrl,
    MessageEntityMention, MessageEntityMentionName
)

BASE    = os.path.dirname(os.path.abspath(__file__))
CONFIG  = os.path.join(BASE, "config.json")
SESSION = os.path.join(BASE, "tg_user_session")
LOG     = os.path.join(BASE, "grab_foreign.log")

API_ID   = 39578814
API_HASH = "18f9ab304c0119a6ab28ff913f02f192"

# ── Каналы-источники ──────────────────────────────────────────────────────────
CHANNELS = [
    "@istorian",
    # добавляй ещё каналы сюда:
    # "@another_history_channel",
]
SCAN_LIMIT    = 200  # сколько сообщений максимум просматриваем за один запуск (в поиске подходящих)
SAVE_PER_RUN  = 5    # сколько НОВЫХ постов сохраняем за один запуск
MAX_STORED    = 60   # не храним больше этого числа постов в foreign/ одновременно
MIN_CHARS     = 1    # берём любой непустой текст

logging.basicConfig(filename=LOG, level=logging.INFO, format="%(asctime)s %(message)s")

# ── SSL ───────────────────────────────────────────────────────────────────────
def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

# ── GitHub API ────────────────────────────────────────────────────────────────
def gh_request(method, path, gh_token, payload=None):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method,
          headers={"Authorization": f"token {gh_token}",
                   "Accept": "application/vnd.github.v3+json",
                   "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20, context=ssl_ctx()) as r:
        return json.loads(r.read())

def gh_get_file(path, gh_token):
    """Возвращает (dict, sha) или ({}, None) если файл не найден."""
    try:
        raw = gh_request("GET", path, gh_token)
        content = base64.b64decode(raw["content"].replace("\n","")).decode("utf-8")
        return json.loads(content), raw["sha"]
    except Exception:
        return {}, None

def gh_put(path, obj, sha, msg, gh_token):
    content = base64.b64encode(json.dumps(obj, ensure_ascii=False, indent=2).encode()).decode()
    payload = {"message": msg, "content": content}
    if sha:
        payload["sha"] = sha
    return gh_request("PUT", path, gh_token, payload)

def gh_put_binary(path, raw_bytes, msg, gh_token):
    """Заливает бинарный файл (картинку) в GitHub. Возвращает raw.githubusercontent.com URL."""
    content = base64.b64encode(raw_bytes).decode()
    payload = {"message": msg, "content": content}
    gh_request("PUT", path, gh_token, payload)
    return f"https://raw.githubusercontent.com/{GH_REPO}/main/{path}"

def gh_list_dir(path, gh_token):
    """Список файлов в папке. Возвращает [] если папка не существует."""
    try:
        return gh_request("GET", path, gh_token)
    except Exception:
        return []

def channel_to_key(channel):
    """@istorian → istorian"""
    return channel.lstrip("@").lower()

# ── Очистка текста от гиперссылок ─────────────────────────────────────────────
def remove_texturl_entities(text, entities):
    """
    Удаляет слова, в которые зашита гиперссылка (MessageEntityTextUrl).
    Telegram использует UTF-16 offset/length.
    """
    if not entities:
        return text

    texturl_ranges = [
        (e.offset, e.offset + e.length)
        for e in entities
        if isinstance(e, MessageEntityTextUrl)
    ]
    if not texturl_ranges:
        return text

    chars = list(text)
    utf16_pos = []
    pos = 0
    for ch in chars:
        utf16_pos.append(pos)
        pos += 2 if ord(ch) >= 0x10000 else 1
    utf16_pos.append(pos)

    result = []
    for i, ch in enumerate(chars):
        cp = utf16_pos[i]
        in_range = any(start <= cp < end for start, end in texturl_ranges)
        if not in_range:
            result.append(ch)

    cleaned = "".join(result)
    cleaned = re.sub(r" {2,}", " ", cleaned).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned

def has_plain_url(msg):
    """True если в посте есть обычная видимая ссылка (реклама/внешняя ссылка)."""
    entities = getattr(msg, "entities", None) or []
    for e in entities:
        if isinstance(e, MessageEntityUrl):
            return True
    text = getattr(msg, "text", None) or getattr(msg, "caption", None) or ""
    if re.search(r"https?://", text):
        return True
    return False

def clean_message(msg):
    """
    Возвращает (cleaned_text, None) если пост подходит,
    или (None, reason) если пост надо пропустить.
    """
    text = getattr(msg, "text", None) or getattr(msg, "caption", None) or ""
    if not text.strip():
        return None, "empty"

    # Пропускаем рекламные/посты с обычными внешними ссылками
    if has_plain_url(msg):
        return None, "ad_or_has_url"

    # Удаляем гиперссылки (слова→ссылка) — это не реклама, просто референс
    entities = getattr(msg, "entities", None) or []
    text = remove_texturl_entities(text, entities)

    if len(text.strip()) < MIN_CHARS:
        return None, "empty_after_clean"

    return text.strip(), None

# ── Основная логика ────────────────────────────────────────────────────────────
async def main():
    with open(CONFIG) as f:
        cfg = json.load(f)
    gh_token = cfg.get("github_token", "")
    global GH_REPO
    GH_REPO = cfg.get("github_repo", "ivanmartynov97/telegram-posts")

    if not gh_token:
        print("❌ github_token не задан в config.json")
        return

    if not os.path.exists(SESSION + ".session"):
        print("❌ Сессия Telethon не найдена. Запусти qr_login.command")
        return

    existing = [f for f in gh_list_dir("foreign", gh_token)
                if f["name"].endswith(".json") and f["name"] != "state.json"]
    if len(existing) >= MAX_STORED:
        print(f"ℹ️ Уже {len(existing)} постов в foreign/ — не добавляем новые")
        print("   Сначала используй или удали часть постов в мини апп")
        return

    state, state_sha = gh_get_file("foreign/state.json", gh_token)

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print("❌ Не авторизован. Запусти qr_login.command")
        await client.disconnect()
        return

    total_saved = 0

    for channel in CHANNELS:
        key = channel_to_key(channel)
        last_id = state.get(key, {}).get("last_id", 0)
        print(f"\n📡 {channel} (продолжаем с msg_id={last_id})")

        try:
            entity = await client.get_entity(channel)
        except Exception as e:
            print(f"   ❌ Не могу получить канал: {e}")
            continue

        try:
            messages = await client.get_messages(
                entity,
                limit=SCAN_LIMIT,
                min_id=last_id,
                reverse=True   # от старых к новым
            )
        except Exception as e:
            print(f"   ❌ Ошибка получения сообщений: {e}")
            continue

        if not messages:
            print(f"   ✅ Новых постов нет")
            continue

        channel_saved = 0
        new_last_id = last_id
        scanned = 0

        for msg in messages:
            if not msg or not msg.id:
                continue
            scanned += 1

            if channel_saved >= SAVE_PER_RUN:
                # Уже набрали нужное число — дальше эти сообщения не трогаем,
                # last_id останавливаем ПЕРЕД текущим, чтобы их пересмотреть в след. раз
                break

            new_last_id = max(new_last_id, msg.id)

            if msg.__class__.__name__ == "MessageService":
                print(f"   ⏭ msg {msg.id}: служебное сообщение — пропуск")
                continue

            if getattr(msg, "fwd_from", None):
                print(f"   ⏭ msg {msg.id}: пересланный — пропуск")
                continue

            text, reason = clean_message(msg)
            if text is None:
                print(f"   ⏭ msg {msg.id}: {reason}")
                continue

            filename = f"foreign/{key}_{msg.id}.json"
            try:
                _, existing_sha = gh_get_file(filename, gh_token)
                if existing_sha:
                    print(f"   ⏭ msg {msg.id}: уже есть")
                    continue

                # Скачиваем фото если есть и перезаливаем на GitHub (если нет фото — берём без него)
                image_url = None
                if getattr(msg, "photo", None):
                    try:
                        photo_bytes = await client.download_media(msg, file=bytes)
                        if photo_bytes:
                            img_path = f"foreign/images/{key}_{msg.id}.jpg"
                            image_url = gh_put_binary(img_path, photo_bytes, f"Foreign image: {channel} #{msg.id}", gh_token)
                            print(f"   🖼  фото скачано и перезалито ({len(photo_bytes)} байт)")
                    except Exception as e:
                        print(f"   ⚠️ не смог скачать фото msg {msg.id}: {e}")

                # Порядковый номер — какой по счёту пост мы взяли из этого канала всего
                seq = state.get(key, {}).get("count", 0) + 1
                if key not in state:
                    state[key] = {}
                state[key]["count"] = seq

                pub_time = msg.date.astimezone(timezone(timedelta(hours=3)))
                record = {
                    "channel": channel,
                    "message_id": msg.id,
                    "seq": seq,
                    "text": text,
                    **({"image_url": image_url} if image_url else {}),
                    "published_at": pub_time.isoformat(),
                    "fetched_at": datetime.now(timezone(timedelta(hours=3))).isoformat(),
                }

                gh_put(filename, record, None, f"Foreign post: {channel} #{msg.id}", gh_token)
                print(f"   ✅ Сохранён msg {msg.id} (#{seq}){' (с фото)' if image_url else ''}: {text[:60]}…")
                channel_saved += 1
                total_saved += 1
            except Exception as e:
                print(f"   ❌ Ошибка сохранения msg {msg.id}: {e}")
                logging.warning(f"{channel} msg {msg.id}: {e}")

        print(f"   (просмотрено {scanned} сообщений)")

        if new_last_id > last_id:
            if key not in state:
                state[key] = {}
            state[key]["last_id"] = new_last_id
            state[key]["updated_at"] = datetime.now(timezone(timedelta(hours=3))).isoformat()

        print(f"   📦 Сохранено {channel_saved} постов")

    if state:
        try:
            gh_put("foreign/state.json", state, state_sha,
                   "Update foreign state", gh_token)
            print(f"\n✅ Готово. Сохранено постов всего: {total_saved}")
        except Exception as e:
            print(f"\n⚠️ Не смог обновить state.json: {e}")

    await client.disconnect()

asyncio.run(main())
