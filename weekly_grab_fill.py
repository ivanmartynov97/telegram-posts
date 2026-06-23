#!/usr/bin/env python3
"""
weekly_grab_fill.py — берёт до N постов из foreign/ (Грабли) по порядку (старые
первыми, по полю seq) и сохраняет их ЛОКАЛЬНО в queue/ как обычные посты с эмодзи
в начале — для еженедельной автогенерации (вторая половина из 42 постов).

Удаляет использованные посты из foreign/ на GitHub (как и ручной pickForeign).

foreign/ — ОБЩИЙ пул для всех каналов (если их несколько): один и тот же сырой пост не
может быть забран дважды, так что каналы автоматически не дублируют друг друга по контенту,
взятому через Грабли. А вот куда СКЛАДЫВАТЬ готовые посты (queue_dir) — управляется аргументом.

Запуск: python3 weekly_grab_fill.py [N] [queue_dir]   (по умолчанию N=21, queue_dir=queue)
"""
import json, os, sys, base64, re, urllib.request, ssl
from datetime import datetime, timezone, timedelta

BASE   = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "config.json")

N = int(sys.argv[1]) if len(sys.argv) > 1 else 21
QUEUE_GH_DIR = sys.argv[2] if len(sys.argv) > 2 else "queue"

with open(CONFIG) as f:
    cfg = json.load(f)
GH_TOKEN = cfg["github_token"]
GH_REPO  = cfg.get("github_repo", "ivanmartynov97/telegram-posts")

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

def gh_get_file(path):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    req = urllib.request.Request(url, headers=gh_headers())
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        data = json.loads(r.read())
    return json.loads(base64.b64decode(data["content"]).decode("utf-8")), data["sha"]

def gh_delete(path, sha, msg):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    payload = {"message": msg, "sha": sha}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="DELETE",
        headers={**gh_headers(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())

def gh_create(path, obj, msg):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    payload = {
        "message": msg,
        "content": base64.b64encode(json.dumps(obj, ensure_ascii=False, indent=2).encode()).decode(),
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="PUT",
        headers={**gh_headers(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())

# Простой подбор эмодзи по ключевым словам (без AI — надёжно для серверного скрипта)
EMOJI_MAP = [
    (r"войн|солдат|армия|битв|сраж|танк|оруж|фронт", "⚔️"),
    (r"космос|спутник|ракет|орбит|гагарин|астронавт", "🚀"),
    (r"корабл|лайнер|флот|моряк|подводн", "🚢"),
    (r"самолёт|авиа|пилот|лётчик", "✈️"),
    (r"автомобил|машин|гонк", "🚗"),
    (r"царь|король|королев|импер|трон|двор|султан|принц", "👑"),
    (r"девуш|женщин|модел|актрис|красав", "💃"),
    (r"учён|наук|изобрет|открыт|механизм|эксперимент", "⚙️"),
    (r"взрыв|катастроф|землетряс|пожар|авари", "💥"),
    (r"деньг|золот|богат|клад|казна|налог", "💰"),
    (r"живот|зверь|собак|кот\b|птиц|лошад", "🐾"),
    (r"фото|снимок|кадр", "📷"),
    (r"тюрьм|казн|смерт|убийств|пытк|расстрел", "☠️"),
    (r"болезн|чум|эпидем|вирус|заражен", "🦠"),
    (r"храм|церков|религ|бог\b|монах", "⛪"),
    (r"закон|суд|приговор|трибунал", "⚖️"),
    (r"карта|путешеств|экспедиц|остров", "🗺️"),
    (r"еда|блюдо|кух|повар|пир", "🍽️"),
    (r"музык|песн|композитор|оркестр", "🎵"),
    (r"книг|писат|роман|поэт|литератур", "📖"),
    (r"искусств|картин|художник|скульптор", "🎨"),
    (r"спорт|олимпиад|чемпион", "🏆"),
    (r"секрет|шпион|заговор|тайн", "🕵️"),
    (r"огонь|вулкан", "🔥"),
    (r"океан|мор[ея]|пират", "🌊"),
]

def pick_emoji(text):
    low = text.lower()
    for pattern, emoji in EMOJI_MAP:
        if re.search(pattern, low):
            return emoji
    return None  # лучше без эмодзи, чем дежурный 📜 не по теме

def add_emoji(text):
    text = text.strip()
    if re.match(r"^[\U0001F300-\U0001FAFF☀-➿]", text):
        return text  # уже есть эмодзи
    emoji = pick_emoji(text)
    return f"{emoji} {text}" if emoji else text

def main():
    items = gh_list("foreign")
    files = [it for it in items if it["type"] == "file" and it["name"].endswith(".json") and it["name"] != "state.json"]
    if not files:
        print("ℹ️ В foreign/ пусто — нечего брать")
        return

    loaded = []
    for it in files:
        try:
            post, sha = gh_get_file(it["path"])
            loaded.append((it, post, sha))
        except Exception as e:
            print(f"⚠️ не смог прочитать {it['name']}: {e}")

    # Сортируем по seq (старые первыми), посты без seq — в конец
    loaded.sort(key=lambda x: x[1].get("seq", 999999))

    take = loaded[:N]
    print(f"Найдено {len(loaded)} постов в foreign/, берём {len(take)} → {QUEUE_GH_DIR}/ на GitHub")

    saved = 0
    for it, post, sha in take:
        text = add_emoji(post.get("text", ""))
        record = {
            "text": text,
            **({"image_url": post["image_url"]} if post.get("image_url") else {}),
            "source_channel": post.get("channel"),
            "source_message_id": post.get("message_id"),
            "from_grabli": True,
            "created_at": datetime.now(timezone(timedelta(hours=3))).isoformat(),
        }
        fname = f"{datetime.now(timezone(timedelta(hours=3))).strftime('%Y%m%d_%H%M%S_%f')}.json"
        try:
            gh_create(f"{QUEUE_GH_DIR}/{fname}", record, f"Weekly grabli: {fname}")
            print(f"  ✅ {QUEUE_GH_DIR}/{fname} ← foreign/{it['name']} (seq={post.get('seq','?')})")
            saved += 1
        except Exception as e:
            print(f"  ❌ не смог записать {fname} в {QUEUE_GH_DIR}/: {e}")
            continue

        try:
            gh_delete(it["path"], sha, f"Used in weekly fill: {it['name']}")
        except Exception as e:
            print(f"     ⚠️ не смог удалить из foreign/: {e}")

    print(f"\n✅ Готово: {saved} постов из Граблей сохранено в {QUEUE_GH_DIR}/ на GitHub")

if __name__ == "__main__":
    main()
