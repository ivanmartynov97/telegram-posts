#!/usr/bin/env python3
"""
Добавляет картинки к постам в очереди через Wikipedia API.
Запуск: python3 add_images.py
"""

import json, os, ssl, glob, time, urllib.request, urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
QUEUE_DIR = os.path.join(BASE, "queue")

# Точные названия Wikipedia-статей для каждого поста (на английском)
WIKI_ARTICLES = {
    "002": "Woolly mammoth",
    "006": "Hero of Alexandria",
    "007": "Tulip mania",
    "008": "Dancing plague of 1518",
    "009": "Voynich manuscript",
    "010": "Emu War",
    "015": "Nikola Tesla",
    "016": "Ada Lovelace",
    "017": "Terracotta Army",
    "018": "Great Wall of China",
    "019": "Catatumbo lightning",
    "020": "Christopher Columbus",
    "021": "Sparta",
    "022": "Elizabeth I",
    "023": "Gladiator",
    "024": "Ancient Egyptian medicine",
    "025": "Julian calendar",
    "026": "Black Death",
    "027": "Defenestrations of Prague",
    "028": "Boston Tea Party",
    "029": "Eiffel Tower",
    "030": "War of Jenkins' Ear",
    "031": "Cherry blossom",
    "032": "Marie Curie",
    "033": "Animal trial",
    "034": "Aeschylus",
    "035": "Yuri Gagarin",
    "036": "Honey",
    "037": "Mary Rose",
    "038": "1815 eruption of Mount Tambora",
    "039": "Compass",
    "040": "Vlad the Impaler",
    "041": "Metric system",
    "042": "Ancient Greek religion",
}

def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def get_thumbnail(article: str) -> str:
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query",
        "titles": article,
        "prop": "pageimages",
        "pithumbsize": 800,
        "format": "json"
    })
    req = urllib.request.Request(url, headers={"User-Agent": "HistoryBot/1.0"})
    with urllib.request.urlopen(req, timeout=10, context=ssl_ctx()) as r:
        data = json.loads(r.read())
    for page in data["query"]["pages"].values():
        src = page.get("thumbnail", {}).get("source", "")
        if src:
            return src
    return ""

def main():
    files = sorted(glob.glob(os.path.join(QUEUE_DIR, "*.json")) +
                   glob.glob(os.path.join(QUEUE_DIR, "reserve", "*.json")))
    print(f"Постов в очереди: {len(files)}\n")
    ok = fail = skip = 0

    for fpath in files:
        num = os.path.basename(fpath).replace(".json", "")
        with open(fpath, encoding="utf-8") as f:
            post = json.load(f)

        if post.get("image_url"):
            print(f"  [{num}] ✅ уже есть картинка")
            skip += 1
            continue

        article = WIKI_ARTICLES.get(num)
        if not article:
            print(f"  [{num}] ⚠️  нет статьи в маппинге")
            fail += 1
            continue

        print(f"  [{num}] \"{article}\"", end=" ... ", flush=True)
        for attempt in range(3):
            try:
                url = get_thumbnail(article)
                if url:
                    post["image_url"] = url
                    with open(fpath, "w", encoding="utf-8") as f:
                        json.dump(post, f, ensure_ascii=False, indent=2)
                    print("✅")
                    ok += 1
                else:
                    print("⚠️  нет картинки в статье")
                    fail += 1
                break
            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    print(f"⏳ rate limit, жду 10 сек...", end=" ", flush=True)
                    time.sleep(10)
                else:
                    print(f"❌ {e}")
                    fail += 1
                    break
        time.sleep(1.5)

    print(f"\nГотово: {ok} с картинкой, {skip} уже были, {fail} без картинки.")

if __name__ == "__main__":
    main()
