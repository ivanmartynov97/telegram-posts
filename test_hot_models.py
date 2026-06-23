#!/usr/bin/env python3
"""
test_hot_models.py — одноразовый тест: добавляет 5 постов категории "горячие модели"
прямо в очередь (queue/) в ближайшие свободные слоты, чтобы визуально проверить
огонёк-эмодзи 🔥 и качество фото (полнокадровые, не обрезанные headshot-портреты).

Подписи простые (без AI — чтобы не требовать Groq-ключ для разового теста),
сам поиск фото — та же логика что в мини-аппе (findHotModelImage).

Запуск: python3 test_hot_models.py
"""
import json, os, base64, random, urllib.request, urllib.parse, ssl
from datetime import datetime, timezone, timedelta

BASE   = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "config.json")
RIGA   = timezone(timedelta(hours=3))
HOURS  = [7, 11, 13, 16, 18, 22]

with open(CONFIG) as f:
    cfg = json.load(f)
GH_TOKEN = cfg["github_token"]
GH_REPO  = "ivanmartynov97/telegram-posts"

HOT_MODEL_NAMES = [
    "Naomi Campbell", "Cindy Crawford", "Claudia Schiffer", "Linda Evangelista",
    "Kate Moss", "Tyra Banks", "Heidi Klum", "Eva Herzigova", "Elle Macpherson",
    "Pamela Anderson", "Rachel Hunter", "Stephanie Seymour", "Adriana Lima",
    "Gisele Bundchen", "Monica Bellucci", "Anna Nicole Smith", "Bettie Page",
    "Cindy Margolis", "Carmen Electra",
]

def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "HistoryBot/1.0"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())

def gh_headers():
    return {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}

def gh_list_queue():
    url = f"https://api.github.com/repos/{GH_REPO}/contents/queue"
    req = urllib.request.Request(url, headers=gh_headers())
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
            items = json.loads(r.read())
        return [it["name"] for it in items if it["type"] == "file"]
    except Exception:
        return []

def gh_create(path, obj):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    payload = {
        "message": f"Test hot model: {path}",
        "content": base64.b64encode(json.dumps(obj, ensure_ascii=False, indent=2).encode()).decode(),
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="PUT",
        headers={**gh_headers(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())

def find_free_slots(n, taken_names):
    """Простой подбор N следующих свободных слотов (без проверки scheduled_at внутри
    файлов — этого достаточно для разового визуального теста)."""
    slots = []
    now = datetime.now(RIGA)
    day = now.date()
    while len(slots) < n:
        for h in HOURS:
            dt = datetime(day.year, day.month, day.day, h, 0, 0, tzinfo=RIGA)
            if dt <= now + timedelta(minutes=10):
                continue
            name = f"slot-{dt.strftime('%Y-%m-%d')}T{h:02d}.json"
            if name in taken_names:
                continue
            slots.append((dt, name))
            taken_names.add(name)
            if len(slots) == n:
                break
        day += timedelta(days=1)
    return slots

def commons_category_photo(name):
    """Большие/полнокадровые фото из категории Commons, без headshot/crop в имени файла."""
    try:
        url = ("https://commons.wikimedia.org/w/api.php?action=query&generator=categorymembers"
               f"&gcmtitle=Category:{urllib.parse.quote(name)}&gcmtype=file&gcmlimit=30"
               "&prop=imageinfo&iiprop=url|size&format=json&origin=*")
        data = http_get(url)
        pages = list(data.get("query", {}).get("pages", {}).values())
        candidates = []
        for p in pages:
            info = (p.get("imageinfo") or [{}])[0]
            u = (info.get("url") or "").lower()
            if not u.endswith((".jpg", ".jpeg")):
                continue
            if any(bad in u for bad in ["map", "flag", "logo", "emblem", "diagram",
                                          "headshot", "face_only", "cropped", "crop_"]):
                continue
            area = (info.get("width") or 0) * (info.get("height") or 0)
            candidates.append((area, info["url"]))
        if not candidates:
            return None
        candidates.sort(key=lambda x: -x[0])
        top = candidates[:10] or candidates
        return random.choice(top)[1]
    except Exception:
        return None

def commons_text_search(query):
    try:
        url = ("https://commons.wikimedia.org/w/api.php?action=query&generator=search"
               f"&gsrsearch={urllib.parse.quote(query)}&gsrnamespace=6&prop=imageinfo&iiprop=url"
               "&format=json&origin=*&gsrlimit=10")
        data = http_get(url)
        pages = list(data.get("query", {}).get("pages", {}).values())
        for p in pages:
            info = (p.get("imageinfo") or [{}])[0]
            u = info.get("url", "")
            if u.lower().endswith((".jpg", ".jpeg")):
                return u
    except Exception:
        pass
    return None

def en_wiki_photo(name):
    try:
        url = ("https://en.wikipedia.org/w/api.php?action=query&titles="
               f"{urllib.parse.quote(name)}&prop=pageimages&pithumbsize=1000&format=json")
        data = http_get(url)
        for page in data.get("query", {}).get("pages", {}).values():
            src = page.get("thumbnail", {}).get("source")
            if src:
                return src
    except Exception:
        pass
    return None

def find_hot_model_image(name):
    return (commons_category_photo(name)
            or commons_text_search(f"{name} magazine cover photoshoot")
            or en_wiki_photo(name))

def main():
    print("🔥 Тестовая генерация 5 постов категории «горячие модели»\n")
    existing = set(gh_list_queue())
    slots = find_free_slots(5, existing)
    names = random.sample(HOT_MODEL_NAMES, 5)

    for (dt, fname), name in zip(slots, names):
        print(f"  {name} → {fname} ({dt.strftime('%d.%m %H:%M')}) ... ", end="", flush=True)
        img = find_hot_model_image(name)
        if not img:
            print("⚠️ фото не нашлось, пропускаю")
            continue
        text = f"🔥 {name} — одна из самых узнаваемых моделей своей эпохи. Её фото расходились по обложкам журналов и закрывали подиумы мировых столиц."
        post = {
            "text": text,
            "image_url": img,
            "scheduled_at": dt.isoformat(),
            "ai_generated": True,
            "test_hot_model": True,
            "created_at": datetime.now(RIGA).isoformat(),
        }
        try:
            gh_create(f"queue/{fname}", post)
            print("✅")
        except Exception as e:
            print(f"❌ {e}")

    print("\nГотово. Открой мини-апп и проверь календарь — посты должны лежать в ближайших слотах.")

if __name__ == "__main__":
    main()
