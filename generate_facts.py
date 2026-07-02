#!/usr/bin/env python3
"""
generate_facts.py — бесконечный генератор уникальных постов через Claude API.
Никогда не повторяется: хранит историю использованных тем в used_topics.json.

Использование:
    python3 generate_facts.py <количество> <queue2|queue3|queue4|queue5>

Примеры:
    python3 generate_facts.py 10 queue3   # 10 фактов о животных/природе
    python3 generate_facts.py 10 queue4   # 10 фактов о науке/природе
    python3 generate_facts.py 10 queue5   # 10 кликбейт-фактов о человеке
    python3 generate_facts.py 10 queue2   # 10 исторических постов
"""
import json, os, sys, ssl, time, random, re, urllib.request, urllib.parse, base64
from datetime import datetime, timezone, timedelta

BASE   = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "config.json")
USED_TOPICS_FILE = os.path.join(BASE, "used_topics.json")

with open(CONFIG) as f:
    cfg = json.load(f)

GH_TOKEN = cfg["github_token"]
GH_REPO  = cfg.get("github_repo", "ivanmartynov97/telegram-posts")
OPENROUTER_KEY = cfg.get("openrouter_key", "") or cfg.get("anthropic_api_key", "")

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# ─── Тематика по очередям ───────────────────────────────────────────────────
QUEUE_PROMPTS = {
    "queue3": {
        "theme": "удивительные факты о животных и природе",
        "style": "научно-популярный стиль, одно конкретное животное или явление природы",
        "example": "🦐 Пистолетная креветка щёлкает клешнёй так быстро, что создаёт пузырёк с температурой 8000°C...",
        "wikipedia_hint": "конкретный вид животного, растения или природного явления — что-то с хорошим фото на Wikipedia"
    },
    "queue4": {
        "theme": "удивительные факты о науке, природе, космосе и технологиях",
        "style": "научно-популярный, немного более серьёзный чем queue3, про открытия и явления",
        "example": "🌲 Деревья общаются через подземный грибковый интернет — 'вуд вайд веб'...",
        "wikipedia_hint": "научная концепция, открытие, природное явление или объект с фото на Wikipedia"
    },
    "queue5": {
        "theme": "шокирующие и неожиданные факты о человеческом теле, психологии и разуме",
        "style": "кликбейт-формат, обращение на 'ты', провокационно, лично касается читателя",
        "example": "😵 Токсоплазмоз — паразит в мозге каждого третьего человека — меняет твою личность...",
        "wikipedia_hint": "медицинская, биологическая или психологическая тема с иллюстрацией на Wikipedia"
    },
    "queue2": {
        "theme": "исторические факты с архивными фотографиями",
        "style": "конкретное историческое событие или открытие, год, реальные детали",
        "example": "✈️ Первый полёт в истории, 1903\n17 декабря 1903 года братья Райт...",
        "wikipedia_hint": "конкретное историческое событие или изобретение, для которого есть архивное фото на Wikipedia"
    }
}

# ─── История использованных тем ─────────────────────────────────────────────

def load_used_topics():
    if os.path.exists(USED_TOPICS_FILE):
        with open(USED_TOPICS_FILE) as f:
            return json.load(f)
    return {"queue2": [], "queue3": [], "queue4": [], "queue5": []}

def save_used_topics(topics):
    with open(USED_TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(topics, f, ensure_ascii=False, indent=2)

# ─── Claude API ─────────────────────────────────────────────────────────────

def call_claude(prompt):
    """Вызывает Claude Haiku через OpenRouter API."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/ivanmartynov97/telegram-posts",
        "X-Title": "TelegramFactsBot"
    }
    body = json.dumps({
        "model": "anthropic/claude-haiku-4-5",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60, context=SSL_CTX) as r:
            data = json.loads(r.read())
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body_err = e.read().decode()
        print(f"  ❌ OpenRouter ошибка {e.code}: {body_err[:300]}")
        return None
    except Exception as e:
        print(f"  ❌ API ошибка: {e}")
        return None

def generate_facts_claude(queue, count, used_topics):
    """Генерирует N новых фактов через Claude, избегая повторов."""
    qp = QUEUE_PROMPTS[queue]
    used_list = used_topics.get(queue, [])

    # Показываем последние 50 использованных тем
    used_str = "\n".join(f"- {t}" for t in used_list[-50:]) if used_list else "- (пока нет)"

    prompt = f"""Ты генерируешь посты для Telegram-канала на тему: {qp['theme']}.

Стиль: {qp['style']}
Пример поста: {qp['example']}

УЖЕ ИСПОЛЬЗОВАННЫЕ ТЕМЫ (их нельзя повторять, найди что-то принципиально другое):
{used_str}

Сгенерируй РОВНО {count} УНИКАЛЬНЫХ постов. Каждый пост должен быть:
1. О НОВОЙ теме (не из списка выше)
2. Содержать конкретный удивительный факт с деталями (числа, названия, имена)
3. Начинаться с подходящего эмодзи
4. Длина: 200-500 символов
5. На русском языке
6. Иметь конкретную статью на Wikipedia с РЕАЛЬНЫМ ФОТО (не SVG, не схема)

Для Wikipedia-поиска выбирай статьи про конкретные объекты/существа/события у которых точно есть фотография.
Хорошие варианты для {queue}: {qp['wikipedia_hint']}

Выведи результат СТРОГО в формате JSON-массива:
[
  {{
    "text": "текст поста",
    "topic": "краткое название темы на английском (для записи в историю)",
    "wikipedia": "точное название статьи Wikipedia на английском"
  }},
  ...
]

ВАЖНО: только JSON, никакого другого текста вокруг. Ровно {count} элементов."""

    print(f"  🤖 Запрос к Claude Haiku ({count} фактов)...")
    response = call_claude(prompt)
    if not response:
        return []

    # Извлекаем JSON из ответа
    try:
        # Ищем JSON-массив в ответе
        match = re.search(r'\[\s*\{.*?\}\s*\]', response, re.DOTALL)
        if match:
            facts = json.loads(match.group())
        else:
            facts = json.loads(response.strip())
        return facts
    except Exception as e:
        print(f"  ❌ Ошибка парсинга JSON: {e}")
        print(f"  Ответ Claude: {response[:500]}")
        return []

# ─── Поиск картинок Wikipedia ────────────────────────────────────────────────

def _pageimages_api(title):
    url = (f"https://en.wikipedia.org/w/api.php?action=query"
           f"&titles={urllib.parse.quote(title)}"
           f"&prop=pageimages&pithumbsize=800&format=json&pilicense=any")
    req = urllib.request.Request(url, headers={"User-Agent": "TelegramBot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as r:
            data = json.loads(r.read())
        for page in data.get("query", {}).get("pages", {}).values():
            src = page.get("thumbnail", {}).get("source", "")
            if src:
                low = src.lower().split("?")[0]
                if low.endswith(".svg") or "/svg/" in low or low.endswith(".gif"):
                    return None
                return src
    except Exception:
        pass
    return None

def _rest_summary(title):
    slug = urllib.parse.quote(title.replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}"
    req = urllib.request.Request(url, headers={"User-Agent": "TelegramBot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as r:
            data = json.loads(r.read())
        src = data.get("thumbnail", {}).get("source", "")
        if src:
            low = src.lower().split("?")[0]
            if not (low.endswith(".svg") or "/svg/" in low or low.endswith(".gif")):
                return src
    except Exception:
        pass
    return None

def _commons_search(query):
    search_url = (f"https://commons.wikimedia.org/w/api.php?action=query&list=search"
                  f"&srsearch={urllib.parse.quote(query)}&srnamespace=6&format=json&srlimit=10")
    req = urllib.request.Request(search_url, headers={"User-Agent": "TelegramBot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as r:
            data = json.loads(r.read())
        for item in data.get("query", {}).get("search", []):
            title = item.get("title", "")
            if not title.startswith("File:"):
                continue
            fname = title[5:]
            ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
            if ext not in ("jpg", "jpeg", "png", "webp"):
                continue
            if any(x in fname.lower() for x in ("icon", "logo", "flag")):
                continue
            info_url = (f"https://commons.wikimedia.org/w/api.php?action=query"
                        f"&titles={urllib.parse.quote(title)}"
                        f"&prop=imageinfo&iiprop=url&iiurlwidth=640&format=json")
            req2 = urllib.request.Request(info_url, headers={"User-Agent": "TelegramBot/1.0"})
            try:
                with urllib.request.urlopen(req2, timeout=8, context=SSL_CTX) as r2:
                    d2 = json.loads(r2.read())
                for p in d2.get("query", {}).get("pages", {}).values():
                    ii = p.get("imageinfo", [{}])[0]
                    thumb = ii.get("thumburl", "") or ii.get("url", "")
                    if thumb:
                        return thumb
            except Exception:
                continue
    except Exception:
        pass
    return None

def find_image(wikipedia_title):
    """Ищет картинку для статьи Wikipedia."""
    queries = [
        wikipedia_title,
        wikipedia_title + " photograph",
    ]
    # Разбиваем на отдельные слова для дополнительных поисков
    words = wikipedia_title.split()
    if len(words) > 1:
        queries.append(words[0])

    for q in queries:
        img = _pageimages_api(q)
        if img:
            return img
        img = _rest_summary(q)
        if img:
            return img

    # Последняя попытка — поиск в Commons
    img = _commons_search(wikipedia_title + " photo")
    return img

# ─── GitHub ──────────────────────────────────────────────────────────────────

GH_HEADERS = {
    "Authorization": f"token {GH_TOKEN}",
    "User-Agent": "Bot/1.0",
    "Accept": "application/vnd.github.v3+json"
}

def gh_push(path, content_str, msg):
    data = json.dumps({
        "message": msg,
        "content": base64.b64encode(content_str.encode()).decode()
    }).encode()
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    req = urllib.request.Request(url, data=data,
        headers={**GH_HEADERS, "Content-Type": "application/json"}, method="PUT")
    try:
        with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ❌ GitHub push error {e.code}: {body[:200]}")
        return None

# ─── Emoji ───────────────────────────────────────────────────────────────────

def load_emoji_ids():
    e1_path = os.path.join(BASE, "emoji1_ids.json")
    e2_path = os.path.join(BASE, "emoji2_ids.json")
    e1 = json.load(open(e1_path)) if os.path.exists(e1_path) else []
    e2 = json.load(open(e2_path)) if os.path.exists(e2_path) else []
    print(f"✅ {len(e1)} emoji1 (Смешарики)")
    print(f"✅ {len(e2)} emoji2")
    return e1, e2

def make_premium_tag(emoji_ids):
    if not emoji_ids:
        return ""
    # emoji_ids может быть dict {emoji: id} или list [id, ...]
    if isinstance(emoji_ids, dict):
        eid = random.choice(list(emoji_ids.values()))
    else:
        eid = random.choice(emoji_ids)
    return f'<tg-emoji emoji-id="{eid}">🔥</tg-emoji>'

# ─── Основная логика ─────────────────────────────────────────────────────────

QUEUE_CONFIG = {
    "queue2": {"dir": "queue2", "channel": "@ricar_telegrama",  "emoji_set": "emoji1"},
    "queue3": {"dir": "queue3", "channel": "@fact_po_secretu",  "emoji_set": "emoji2"},
    "queue4": {"dir": "queue4", "channel": "@umnaya_utka",       "emoji_set": "emoji1"},
    "queue5": {"dir": "queue5", "channel": "@umnim_vhod",        "emoji_set": "emoji2"},
}

def main():
    if len(sys.argv) < 3:
        print("Использование: python3 generate_facts.py <количество> <queue2|queue3|queue4|queue5>")
        sys.exit(1)

    count = int(sys.argv[1])
    queue = sys.argv[2].lower()

    if queue not in QUEUE_CONFIG:
        print(f"Неизвестная очередь: {queue}")
        sys.exit(1)

    if not OPENROUTER_KEY:
        print("❌ openrouter_key не указан в config.json")
        sys.exit(1)

    qcfg = QUEUE_CONFIG[queue]
    emoji1_ids, emoji2_ids = load_emoji_ids()
    emoji_ids = emoji1_ids if qcfg["emoji_set"] == "emoji1" else emoji2_ids

    # Загружаем историю использованных тем
    used_topics = load_used_topics()

    print(f"\n=== Генерируем {count} фактов для {queue} ({qcfg['channel']}) ===")
    print(f"  Уже использовано тем: {len(used_topics.get(queue, []))}")

    # Генерируем факты через Claude
    # Запрашиваем больше чем нужно — некоторые могут не найти картинку
    batch_size = min(count * 2, count + 10)
    facts = generate_facts_claude(queue, batch_size, used_topics)

    if not facts:
        print("  ❌ Claude не вернул факты")
        sys.exit(1)

    print(f"  ✅ Claude вернул {len(facts)} фактов, ищем картинки...")

    pushed = 0
    new_topics = []

    for i, fact in enumerate(facts):
        if pushed >= count:
            break

        text = fact.get("text", "").strip()
        topic = fact.get("topic", f"topic_{i}")
        wiki_title = fact.get("wikipedia", "")

        if not text or not wiki_title:
            continue

        print(f"\n  [{pushed+1}/{count}] 🔍 {topic}")

        # Ищем картинку
        img_url = find_image(wiki_title)
        if not img_url:
            print(f"    ⚠️  Нет картинки для '{wiki_title}' — пропускаем")
            continue

        print(f"    🖼  {img_url[:70]}...")

        # Добавляем premium emoji в конец текста
        premium = make_premium_tag(emoji_ids)
        full_text = text + ("\n" + premium if premium else "")

        # Создаём JSON файл
        ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{ts % 10000}.json"
        filepath = f"{qcfg['dir']}/{filename}"

        post = {
            "text": full_text,
            "image_url": img_url,
            "channel": qcfg["channel"],
            "topic": topic,
            "generated_by": "claude-haiku",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        result = gh_push(filepath, json.dumps(post, ensure_ascii=False, indent=2),
                         f"Add {queue} fact: {topic}")
        if result:
            print(f"    ✅ Запушено: {filename}")
            pushed += 1
            new_topics.append(topic)
            time.sleep(0.5)
        else:
            print(f"    ❌ Ошибка push")

    # Сохраняем использованные темы
    if new_topics:
        used_topics.setdefault(queue, []).extend(new_topics)
        save_used_topics(used_topics)
        print(f"\n✅ Сохранено {len(new_topics)} новых тем в историю")

    print(f"\n✅ Готово! Запушено {pushed}/{count} постов в {queue}")

if __name__ == "__main__":
    main()
