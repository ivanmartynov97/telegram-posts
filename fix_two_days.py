#!/usr/bin/env python3
"""Чинит 5 постов: добавляет фото (retry + альтернативные запросы) и переписывает хуки."""
import json, os, base64, urllib.request, urllib.parse, ssl, time
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, "config.json")) as f:
    cfg = json.load(f)
GH_TOKEN = cfg["github_token"]
GH_REPO  = cfg.get("github_repo", "ivanmartynov97/telegram-posts")

def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "HistoryBot/1.0"})
    with urllib.request.urlopen(req, timeout=12, context=ssl_ctx()) as r:
        return json.loads(r.read())

def wiki_image(query, lang="en", retries=4):
    for attempt in range(retries):
        try:
            s = fetch_json(f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
                "action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": 1
            }))
            hits = s.get("query", {}).get("search", [])
            if not hits:
                return None
            title = hits[0]["title"]
            p = fetch_json(f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
                "action": "query", "titles": title, "prop": "pageimages", "pithumbsize": 800, "format": "json"
            }))
            for page in p.get("query", {}).get("pages", {}).values():
                src = page.get("thumbnail", {}).get("source")
                if src:
                    return src
            return None
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                wait = 5 * (attempt + 1)
                print(f"   ⏳ 429, жду {wait}с...")
                time.sleep(wait)
            else:
                print(f"   ⚠️ {e}")
                return None
    return None

def commons_image(query):
    """Фоллбэк: текстовый поиск картинок прямо в Wikimedia Commons."""
    try:
        r = fetch_json("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "generator": "search", "gsrsearch": query, "gsrnamespace": 6,
            "prop": "imageinfo", "iiprop": "url", "format": "json", "gsrlimit": 5
        }))
        pages = r.get("query", {}).get("pages", {})
        for p in pages.values():
            url = p.get("imageinfo", [{}])[0].get("url", "")
            if url and not url.lower().endswith(".svg"):
                return url
    except Exception as e:
        print(f"   ⚠️ commons_image({query}): {e}")
    return None

def gh_get(path):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        data = json.loads(r.read())
    content = json.loads(base64.b64decode(data["content"]).decode("utf-8"))
    return content, data["sha"]

def gh_put(path, obj, sha, msg):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    payload = {
        "message": msg,
        "content": base64.b64encode(json.dumps(obj, ensure_ascii=False, indent=2).encode()).decode(),
        "sha": sha,
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="PUT",
        headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())

FIXES = {
    "slot-2026-06-21T18.json": {
        "image_query": "Belka and Strelka", "lang": "en",
        "text": "🐕🚀 Эти две собаки облетели Землю раньше, чем это сделал хоть один человек — и вернулись живыми.\n\n19 августа 1960 года Белка и Стрелка стали первыми живыми существами на орбите, успешно возвратившимися на Землю. Стрелка позже родила щенков — одного из них, Пушинку, советское правительство подарило дочери президента Кеннеди.",
    },
    "slot-2026-06-21T22.json": {
        "image_query": "Tsutomu Yamaguchi", "lang": "en",
        "text": "☢️ Этот человек пережил не одну, а две атомные бомбардировки подряд.\n\nЦутому Ямагути получил ожоги в Хиросиме 6 августа 1945 года, но выжил и на следующий день вернулся домой — в Нагасаки. 9 августа там взорвалась вторая бомба. Он выжил и во второй раз — единственный человек, официально признанный Японией пострадавшим от обеих бомбардировок.",
    },
    "slot-2026-06-22T07.json": {
        "image_query": "Antikythera mechanism", "lang": "en",
        "text": "⚙️ На дне моря нашли бронзовый механизм возрастом более 2000 лет — с шестернями точнее, чем в европейских часах XIV века.\n\nВ 1901 году греческие водолазы поднял Антикитерский механизм, предсказывавший движение Солнца, Луны и затмения. Понадобилось сто лет рентгеновских снимков, чтобы понять, как он работает.",
    },
    "slot-2026-06-22T11.json": {
        "image_query": "Sputnik 1", "lang": "en",
        "text": "🛰️ Простой сигнал «бип-бип» услышал весь мир — его передавал первый искусственный спутник Земли.\n\nСпутник-1 запустили в СССР 4 октября 1957 года. Весил всего 83.6 кг, а сигнал можно было поймать обычным радиоприёмником — что и сделали миллионы людей по всей планете.",
    },
    "slot-2026-06-22T18.json": {
        "image_query": "Secchia rapita Modena Bologna bucket",
        "commons_query": "War of the Bucket Modena 1325",
        "lang": "en",
        "text": "🪣 Две итальянские армии устроили настоящую войну из-за украденного деревянного ведра.\n\nВ 1325 году солдаты Модены выкрали из колодца обычное дубовое ведро как акт издевательства над Болоньей. Та восприняла это как смертельное оскорбление и собрала армию в 32 000 человек. В битве при Цаппольно Модена, имея втрое меньше войск, разгромила болонцев — и ведро осталось в Модене, где висит в башне до сих пор.",
    },
    # Бонус-фикс хуков (без проблем с фото, но начинались с даты)
    "slot-2026-06-21T11.json": {
        "text": "💥 Что-то взорвалось над Сибирью с силой в 1000 Хиросим — и не оставило после себя ни кратера, ни осколков.\n\n30 июня 1908 года Тунгусский метеорит (вероятно, ледяная комета, взорвавшаяся в воздухе) повалил 80 миллионов деревьев на территории 2150 км². Если бы он влетел на 4-5 часов позже, взрыв пришёлся бы на Санкт-Петербург.",
    },
    "slot-2026-06-21T16.json": {
        "text": "💃 Одна женщина вышла на улицу и начала танцевать без музыки — и не могла остановиться несколько дней. К ней присоединились ещё около 400 человек.\n\nЛетом 1518 года в Страсбурге разразилась «танцевальная чума»: горожане танцевали без остановки, некоторые — до смерти от истощения. Городской совет решил, что танец — это болезнь, и наняла музыкантов чтобы «вылечить» танцоров музыкой — что лишь усилило эпидемию.",
    },
}

def main():
    for name, fix in FIXES.items():
        path = f"queue/{name}"
        print(f"{name}:", end=" ")
        try:
            post, sha = gh_get(path)
        except Exception as e:
            print(f"❌ не найден на GitHub (возможно уже опубликован): {e}")
            continue

        changed = False
        if "text" in fix:
            post["text"] = fix["text"]
            changed = True

        if "image_query" in fix and not post.get("image_url"):
            img = wiki_image(fix["image_query"], fix.get("lang", "en"))
            if not img and "commons_query" in fix:
                img = commons_image(fix["commons_query"])
            if img:
                post["image_url"] = img
                print(f"фото найдено ✅", end=" ")
                changed = True
            else:
                print("фото так и не нашлось ⚠️", end=" ")

        if changed:
            try:
                gh_put(path, post, sha, f"Fix: {name}")
                print("— сохранено")
            except Exception as e:
                print(f"— ❌ ошибка сохранения: {e}")
        else:
            print("— без изменений")
        time.sleep(1)

if __name__ == "__main__":
    main()
