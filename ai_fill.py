#!/usr/bin/env python3
"""
ai_fill.py — серверный (без браузера/мини-аппа) аналог AI-вкладки index.html.
Генерирует N постов через Groq (текст с крючком+эмодзи) + ищет картинку через
Wikipedia/Commons, сохраняет в queue/queue2 на GitHub С ЧЕРЕДОВАНИЕМ относительно
уже лежащих там "грабли"-постов (по явной просьбе — не сплошным блоком).

Запуск: GROQ_KEY=gsk_... python3 ai_fill.py <N> <queue_dir>
Запасной провайдер (22.06, на случай когда у Groq кончилась бесплатная квота прямо
во время работы): GROQ_KEY=gsk_... OPENROUTER_KEY=sk-or-v1-... python3 ai_fill.py ...
— если Groq отвечает лимитом (429) на всех попытках, скрипт автоматически переходит
на OpenRouter (DeepSeek и другие бесплатные ":free" модели), без участия пользователя.
OPENROUTER_KEY опционален — без него поведение как раньше (просто падает на ошибке Groq).
"""
import json, os, re, sys, time, base64, ssl, urllib.request, urllib.parse, random
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "config.json")
RIGA_TZ = timezone(timedelta(hours=3))

N = int(sys.argv[1]) if len(sys.argv) > 1 else 14
QUEUE_DIR = sys.argv[2] if len(sys.argv) > 2 else "queue"
THEME = sys.argv[3] if len(sys.argv) > 3 else "history"  # "history" или "facts"
GROQ_KEY = os.environ.get("GROQ_KEY")
if not GROQ_KEY:
    print("❌ Нет GROQ_KEY в окружении")
    sys.exit(1)
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY")  # опционально — запасной провайдер

with open(CONFIG) as f:
    cfg = json.load(f)
GH_TOKEN = cfg["github_token"]
GH_REPO = cfg.get("github_repo", "ivanmartynov97/telegram-posts")
# Стиль картинок из config.json для данного канала (поле image_style) — позволяет каждому
# каналу иметь свой визуальный почерк, например мультяшный vs кинематографический.
IMAGE_STYLE = next((ch.get("image_style") for ch in cfg.get("channels", []) if ch.get("queue_dir") == QUEUE_DIR), None)


def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def gh_headers():
    return {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}


def gh_list(path):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    req = urllib.request.Request(url, headers=gh_headers())
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
            return json.loads(r.read())
    except Exception:
        return []


def gh_create(path, obj, msg):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    payload = {"message": msg, "content": base64.b64encode(json.dumps(obj, ensure_ascii=False, indent=2).encode()).decode()}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="PUT",
        headers={**gh_headers(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20, context=ssl_ctx()) as r:
        return json.loads(r.read())


# БАГ-ФИКС (22.06, реальный инцидент — queue4 не заполнился вообще): "llama-3.1-70b-versatile"
# был decommissioned Groq'ом и теперь отвечает HTTP 400 "model_decommissioned", а не 429.
# Раньше любая НЕ-рейтлимит ошибка сразу выбрасывалась наружу, обрывая всю генерацию —
# то есть стоило цепочке дойти до этой мёртвой модели, и упор в HTTP 400 крашил весь батч,
# даже не пробуя оставшиеся модели/OpenRouter. Убрали мёртвую модель из списка.
GROQ_MODEL_FALLBACKS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it"]
# Запасной провайдер OpenRouter (22.06, добавлено когда queue4/Умная утка не смог
# заполниться вообще — Groq упёрся в дневной 429 на всех 4 моделях). Тот же
# OpenAI-совместимый формат, просто другой хост/ключ/модели. DeepSeek первый —
# по качеству русского среди бесплатных моделей заметно лучше Llama.
# deepseek/deepseek-chat-v3-0324:free и deepseek/deepseek-r1:free убраны с бесплатного
# доступа OpenRouter (HTTP 404 "unavailable for free"). Актуальный список:
OPENROUTER_MODEL_FALLBACKS = [
    "meta-llama/llama-3.3-70b-instruct:free",     # хороший русский, если не rate-limited
    "google/gemma-3-27b-it:free",                 # Google Gemma 3, бесплатный
    "deepseek/deepseek-v3-base:free",             # DeepSeek v3, хороший русский
    "qwen/qwen3-8b:free",                         # Qwen3, достаточно хороший русский
    "meta-llama/llama-3.1-8b-instruct:free",      # меньший Llama fallback
    "microsoft/phi-3-mini-128k-instruct:free",    # крайний случай
    # mistralai/mistral-7b-instruct:free убран — вернул 404 (убран с free tier)
]


def _is_rate_limit_error(e):
    msg = str(e)
    return "429" in msg or "rate" in msg.lower() or "quota" in msg.lower() or "capacity" in msg.lower()


def _status_code(e):
    return getattr(e, "code", None)


def _http_chat(url, api_key, model, messages, max_tokens, extra_headers=None):
    body = json.dumps({"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.9}).encode()
    headers = {
        "Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
        # БАГ-ФИКС "HTTP 403 / error code 1010": это не проблема ключа — Cloudflare на
        # стороне api.groq.com блокирует запросы с дефолтным User-Agent урлиба
        # ("Python-urllib/3.x") как похожие на бота. Обычный браузерный UA решает это.
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    }
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    with urllib.request.urlopen(req, timeout=30, context=ssl_ctx()) as r:
        data = json.loads(r.read())
        return data["choices"][0]["message"]["content"]


def _try_model(url, api_key, gmodel, messages, max_tokens, retries, extra_headers=None):
    """Пробует ОДНУ модель до retries раз. Возвращает текст или бросает последнюю ошибку."""
    last_err = None
    for attempt in range(retries):
        try:
            return _http_chat(url, api_key, gmodel, messages, max_tokens, extra_headers)
        except Exception as e:
            last_err = e
            code = _status_code(e)
            # БАГ-ФИКС: 400/401/404 повторять бессмысленно — выходим сразу.
            # 401 = невалидный ключ; 400/404 = модель недоступна/decommissioned.
            if code in (400, 401, 404) or not _is_rate_limit_error(e):
                break
            time.sleep(3)
    raise last_err


def groq_chat(messages, max_tokens=300, model="llama-3.3-70b-versatile", retries=3):
    url = "https://api.groq.com/openai/v1/chat/completions"
    or_url = "https://openrouter.ai/api/v1/chat/completions"
    or_headers = {"HTTP-Referer": "https://ivanmartynov97.github.io", "X-Title": "History+ ai_fill.py"}
    last_err = None
    # 1) Основная сильная модель Groq.
    try:
        return _try_model(url, GROQ_KEY, model, messages, max_tokens, retries)
    except Exception as e:
        last_err = e
        print(f"  ⚠️ Groq: модель {model} недоступна ({e}), пробую OpenRouter…")
    # 2) БАГ-ФИКС (22.06, жалоба "посты кривые, с кучей ошибок"): раньше при лимите
    # основной модели сразу шли слабые Groq-модели (8b/9b) — они регулярно ломают
    # русскую грамматику ("Больной человека сожрает", "Побеги на длинные дистанции"
    # вместо "Бег"). OpenRouter/DeepSeek пишет по-русски заметно чище — теперь он
    # пробуется ПЕРЕД слабыми моделями, а не после них.
    if OPENROUTER_KEY:
        for ormodel in OPENROUTER_MODEL_FALLBACKS:
            try:
                print(f"  ↪ Пробую OpenRouter ({ormodel})…")
                # retries=1 — на 429 сразу к следующей модели (free tier не восстановится за 3с)
                return _try_model(or_url, OPENROUTER_KEY, ormodel, messages, max_tokens, 1, or_headers)
            except Exception as e:
                last_err = e
                print(f"  ⚠️ OpenRouter: модель {ormodel} недоступна ({e}), пробую другую…")
    # 3) Крайний случай — слабые модели Groq хуже по качеству, но лучше, чем ничего.
    for gmodel in [m for m in GROQ_MODEL_FALLBACKS if m != model]:
        try:
            print(f"  ↪ Крайний случай: пробую слабую модель Groq ({gmodel})…")
            return _try_model(url, GROQ_KEY, gmodel, messages, max_tokens, retries)
        except Exception as e:
            last_err = e
            print(f"  ⚠️ Groq: модель {gmodel} недоступна ({e}), пробую другую модель…")
    raise last_err


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())


def is_relevant(query, title, strict=False):
    """Проверяет совпадение запроса с заголовком найденного результата.
    strict=True требует минимум 2 совпавших слова (или все, если запрос короткий).
    strict=False — хотя бы 1 слово. Для поиска картинок к постам используем strict=True
    чтобы не брать неуместные фото."""
    qw = set(re.sub(r"[^\w\s]", " ", query.lower()).split())
    tw = set(re.sub(r"[^\w\s]", " ", title.lower()).split())
    qw = {w for w in qw if len(w) > 2}
    if not qw:
        return False
    overlap = len(qw & tw)
    if strict:
        needed = min(2, len(qw))  # нужно минимум 2 или все слова если их меньше 2
        return overlap >= needed
    return overlap >= 1


def fetch_en_wiki_photo(query):
    try:
        surl = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json&srlimit=3"
        s = fetch_json(surl)
        for hit in s.get("query", {}).get("search", []):
            if not is_relevant(query, hit["title"]):
                continue
            purl = f"https://en.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(hit['title'])}&prop=pageimages&pithumbsize=800&format=json"
            p = fetch_json(purl)
            pages = p.get("query", {}).get("pages", {})
            for pg in pages.values():
                thumb = pg.get("thumbnail", {}).get("source")
                if thumb:
                    return thumb
    except Exception:
        pass
    return None


def fetch_commons_photo(query, require_match=True):
    try:
        surl = f"https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}%20filetype:bitmap&srnamespace=6&format=json&srlimit=5"
        s = fetch_json(surl)
        for hit in s.get("query", {}).get("search", []):
            title = hit["title"]
            if require_match and not is_relevant(query, title):
                continue
            fname = title.replace("File:", "")
            iurl = f"https://commons.wikimedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}&prop=imageinfo&iiprop=url&iiurlwidth=800&format=json"
            info = fetch_json(iurl)
            pages = info.get("query", {}).get("pages", {})
            for pg in pages.values():
                ii = pg.get("imageinfo", [{}])[0]
                url = ii.get("thumburl") or ii.get("url")
                if url:
                    return url
    except Exception:
        pass
    return None


def find_image(img_query):
    if not img_query:
        return None
    img = fetch_commons_photo(img_query) or fetch_en_wiki_photo(img_query)
    if img:
        return img
    # Фолбэк: первые 2 слова (не 1 — одно слово слишком широко и даёт нерелевантные фото)
    parts = img_query.split()
    if len(parts) >= 2:
        two = " ".join(parts[:2])
        return fetch_commons_photo(two, require_match=True) or fetch_en_wiki_photo(two)
    return None


HOOK_EXAMPLES = (
    'ПРИМЕРЫ ХОРОШИХ крючков: "Этот человек обманул смерть дважды за три дня", '
    '"Армия сдалась — но только потому что перепутали время", '
    '"Никто не должен был узнать об этом письме — но узнал весь мир".\n'
    'ПРИМЕРЫ ПЛОХИХ крючков (никогда так не пиши): "5 марта 1953 года умер...", '
    '"Иосиф Сталин был известен тем что...", "В истории есть много интересных фактов о...".'
)


FACT_EXAMPLES = (
    'ПРИМЕРЫ ФОРМАТА (бери за образец СТРУКТУРУ И КЛИКБЕЙТНОСТЬ, не темы):\n'
    '"🥩 Красное мясо вызывает рак — даже в небольших количествах регулярное употребление '
    'переработанного мяса повышает риск онкологии кишечника, предупреждает ВОЗ."\n'
    '"🔞 Секс полезен для иммунитета — во время близости вырастает уровень иммуноглобулина A, '
    'который защищает организм от простуды и вирусов."\n'
    '"🧠 Жвачка во время учёбы улучшает память — жевательное движение усиливает приток крови '
    'к мозгу и помогает сосредоточиться на 10-15%."\n'
    '"💋 Поцелуй сжигает больше калорий, чем ты думаешь — 2-6 калорий в минуту, а при страстном '
    'поцелуе пульс подскакивает как на лёгкой тренировке."'
)


def gen_text(n, used_topics=None):
    used_str = ""
    if used_topics:
        used_str = f"\nУЖЕ ИСПОЛЬЗОВАННЫЕ ТЕМЫ (не повторяй даже близко): {', '.join(list(used_topics)[:30])}\n"

    if THEME == "facts":
        prompt = f"""Ты автор КЛИКБЕЙТНОГО Telegram-канала о фактах на русском языке.

Напиши {n} коротких фактов-утверждений.

{FACT_EXAMPLES}
{used_str}
ЖЁСТКИЕ ПРАВИЛА:
• Пиши СРАЗУ НА РУССКОМ — не переводи с английского, не кальки. Факты из русскоязычных источников.
• Только ПРОВЕРЕННЫЕ, реальные факты — никаких выдумок.
• МАКСИМАЛЬНО КЛИКБЕЙТНАЯ первая часть — шок, провокация, неожиданность. Темы: здоровье, тело, психология, наука, природа, еда, отношения, секс — чередовать.
• Примерно КАЖДЫЙ 5-6-Й — тема секса/близости/тела, подача как у медицинского паблика, без пошлости.
• Каждый пост — УНИКАЛЬНАЯ, ДРУГАЯ тема (не повторять даже похожие).
• 1 эмодзи В НАЧАЛЕ, отражающий тему.
• Длина — 60-220 символов на пост.
• Ни одного слова на английском.
• Без слов "факт"/"знаете ли вы" — сразу утверждение.
• ЗАПРЕЩЕНО начинать с названия категории: "Здоровье:", "Секс:", "Природа:" и т.д.

ФОРМАТ КАЖДОГО ПОСТА (строго):
TEXT: <текст поста с эмодзи>
IMG: <главный предмет/явление, 1-3 слова НА АНГЛИЙСКОМ для поиска фото в Wikipedia>

Разделяй посты строкой "---". Не нумеруй, не добавляй пояснений."""
    else:
        prompt = f"""Ты автор вирусного Telegram-канала "History+" об истории.

Напиши {n} постов об истории.

ЖЁСТКИЕ ПРАВИЛА:
• Первая строка — ЖИВОЙ КРЮЧОК (5-10 слов): шок, парадокс, провокация. ЗАПРЕЩЕНО начинать с имени, даты, "Он", "Она", "В", "Когда".
{HOOK_EXAMPLES}
• После крючка — 2-4 предложения: контекст, детали, вывод или ирония.
• ОБЯЗАТЕЛЬНО: в каждом посте должно быть конкретное имя (человека/места/события/организации) и/или точная дата или год. ЗАПРЕЩЕНО писать "один человек", "некий генерал", "один город", "некая страна", "какой-то парк" и другие безымянные описания — только настоящие имена собственные.
• Длина — РАЗНАЯ для разных постов: ~45% постов 50-150 символов, ~35% 150-280 символов, ~20% 280-550 символов.
• 1-2 эмодзи в начале — ОБЯЗАТЕЛЬНО, отражают тему поста (не случайные).
• Каждый пост — РАЗНАЯ эпоха и тема (разные века, разные страны).
• Пиши ВЕСЬ текст полностью на русском языке. Ни одного слова на английском.
• Выводи СРАЗУ готовый текст — без преамбул, без слов "крючок"/"заголовок"/"детали" в тексте.

ФОРМАТ КАЖДОГО ПОСТА (строго):
TEXT: <текст поста с эмодзи>
IMG: <главный человек/место/событие/предмет, КОРОТКОЙ ФРАЗОЙ НА АНГЛИЙСКОМ для поиска фото>

Разделяй посты строкой "---". Не нумеруй, не добавляй пояснений."""
    raw = groq_chat([{"role": "user", "content": prompt}], max_tokens=2200 + n * 70)
    blocks = [b.strip() for b in re.split(r"\n?-{3,}\n?", raw) if b.strip()]
    parsed = []
    for b in blocks:
        tm = re.search(r"TEXT:\s*([\s\S]*?)(?=\s*\bIMG:|\s*$)", b, re.I)
        im = re.search(r"\bIMG:\s*(.+)", b, re.I)
        text = tm.group(1).strip() if tm else b
        text = re.sub(r"\bIMG:[\s\S]*$", "", text, flags=re.I).strip()
        # БАГ-ФИКС (23.06): llama-3.3-70b иногда нумерует блоки "**Пост N**" или "### Пост N"
        # в начале, а потом пишет текст без "TEXT:" — вся строка "**Пост N**\n" попадает в text.
        # Срезаем любую markdown-нумерацию в начале блока: **..N..** / ##...N / [Пост N] и т.п.
        text = re.sub(r"^[\*#\[]*\s*(?:Пост|Post)\s*\d+[\s\*#\]]*\n*", "", text, flags=re.I).strip()
        # БАГ-ФИКС (22.06, реальный случай в queue4 — "Solar Flare"/"Erectalis"/"Murder" и
        # т.п. приклеились к концу опубликованного текста): слабые fallback-модели иногда
        # пишут короткую "подсказку для картинки" БЕЗ префикса "IMG:" отдельной строкой
        # перед настоящей строкой "IMG: ...". Без префикса наш лэйзи-регекс выше не отличает
        # её от текста поста и она остаётся приклеенной в конце. Эвристика: такой "хвост" —
        # короткая (1-5 слов) строка из ТОЛЬКО латинских букв после пустой строки, тогда как
        # реальный текст поста всегда на русском — безопасно срезаем.
        text = re.sub(r"\n\s*\n[A-Za-z][A-Za-z\s]{1,40}$", "", text).strip()
        # БАГ-ФИКС (жалоба "зачем первым слово идёт тема? типа Здоровье: Медицина:"):
        # запрет в промпте не всегда соблюдается слабыми моделями — добавлена защитная
        # подчистка: срезаем "Слово(а):" сразу после эмодзи в начале текста (категория-
        # этикетка вместо крючка), если за ним идёт реальный текст факта.
        text = re.sub(r"^(\S+\s*)[А-ЯA-Z][а-яёa-zA-Z]{2,16}(?:\s[А-ЯA-Z][а-яёa-zA-Z]{2,16})?:\s+", r"\1", text)
        img_query = im.group(1).strip().strip('"\'.') if im else None
        if len(text) > 60:
            parsed.append({"text": text, "img_query": img_query})
    return parsed


def main():
    print(f"=== Генерируем {N} AI-постов для {QUEUE_DIR} ===")
    candidates = []
    used_topics = set()  # дедупликация тем внутри батча
    target_buffer = N + max(4, int(N * 0.5))
    attempts = 0
    while len(candidates) < N and attempts < 4:
        need = target_buffer - len(candidates)
        batch = gen_text(need, used_topics)
        for item in batch:
            # Для всех каналов — Wikipedia/Commons (реальные фото, не AI-мусор).
            # Модель уже даёт img_query на английском (1-3 слова) — ищем по нему.
            img = find_image(item["img_query"])
            # Если Wikipedia ничего не нашла — пост всё равно берём, просто без картинки
            # (лучше реальный текст без фото, чем AI-бред с картинкой).
            # Дедупликация: пропускаем посты с почти той же темой что уже есть в батче.
            first_words = " ".join(item["text"].split()[:4])
            if first_words in used_topics:
                continue
            used_topics.add(first_words)
            candidates.append({"text": item["text"], "image_url": img})
            if len(candidates) >= target_buffer:
                break
        attempts += 1
    candidates = candidates[:N]
    print(f"Готово текстов: {len(candidates)} из {N} запрошенных, с картинками: {sum(1 for c in candidates if c['image_url'])}")

    # Чередование: вставляем AI-посты МЕЖДУ уже существующими грабли-постами в queue_dir,
    # сдвигая каждый на +2 секунды от соответствующего грабли-файла, чтобы при сортировке
    # по имени (так auto_publish.py раздаёт слоты) порядок шёл вперемешку, а не блоками.
    items = gh_list(QUEUE_DIR)
    existing = sorted([it["name"] for it in items if it.get("type") == "file" and it["name"].endswith(".json")])
    grabli_times = []
    for name in existing:
        m = re.match(r"(\d{8})_(\d{6})_(\d+)\.json", name)
        if m:
            dt = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").replace(tzinfo=RIGA_TZ)
            grabli_times.append(dt)
    grabli_times.sort()

    saved = 0
    for i, post in enumerate(candidates):
        if i < len(grabli_times):
            ts = grabli_times[i] + timedelta(seconds=2)
        else:
            ts = datetime.now(RIGA_TZ) + timedelta(seconds=i)
        fname = ts.strftime("%Y%m%d_%H%M%S_") + f"{random.randint(100000,999999)}.json"
        # Подпись для канала "Умная утка" (queue4) — добавляем в конце каждого поста
        post_text = post["text"]
        if QUEUE_DIR == "queue4":
            post_text = post_text.rstrip() + "\n\nСтавьте лайк 👍, если не знали. Кря! 🦆"
        record = {
            "text": post_text,
            "image_url": post["image_url"],
            "from_ai": True,
            "created_at": datetime.now(RIGA_TZ).isoformat(),
        }
        try:
            gh_create(f"{QUEUE_DIR}/{fname}", record, f"AI post for {QUEUE_DIR}")
            print(f"  ✅ {QUEUE_DIR}/{fname}: {post['text'][:50]!r}")
            saved += 1
            time.sleep(1)
        except Exception as e:
            print(f"  ❌ не сохранил: {e}")

    print(f"\n✅ Сохранено {saved} AI-постов в {QUEUE_DIR}/ (чередуются с грабли по времени слотов)")


if __name__ == "__main__":
    main()
