#!/usr/bin/env python3
"""
Дозаполняет старые посты в foreign/ (сохранённые до того, как появилась загрузка фото):
- Перечитывает оригинальное сообщение в канале-доноре по message_id
- Если там есть фото — скачивает и прикрепляет (обновляет тот же файл, не удаляя)
- Добавляет порядковый номер seq, если его не было
"""
import asyncio, json, os, base64, ssl, urllib.request
from telethon import TelegramClient

BASE    = os.path.dirname(os.path.abspath(__file__))
CONFIG  = os.path.join(BASE, "config.json")
SESSION = os.path.join(BASE, "tg_user_session")
API_ID   = 39578814
API_HASH = "18f9ab304c0119a6ab28ff913f02f192"

def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def gh_headers(token):
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

def gh_list(path, token, repo):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    req = urllib.request.Request(url, headers=gh_headers(token))
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())

def gh_get_file(path, token, repo):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    req = urllib.request.Request(url, headers=gh_headers(token))
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        data = json.loads(r.read())
    return json.loads(base64.b64decode(data["content"]).decode("utf-8")), data["sha"]

def gh_put(path, obj, sha, token, repo, msg):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    payload = {"message": msg, "content": base64.b64encode(json.dumps(obj, ensure_ascii=False, indent=2).encode()).decode(), "sha": sha}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="PUT", headers={**gh_headers(token), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())

def gh_put_binary(path, raw_bytes, token, repo, msg):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    payload = {"message": msg, "content": base64.b64encode(raw_bytes).decode()}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="PUT", headers={**gh_headers(token), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20, context=ssl_ctx()) as r:
        json.loads(r.read())
    return f"https://raw.githubusercontent.com/{repo}/main/{path}"

async def main():
    with open(CONFIG) as f:
        cfg = json.load(f)
    gh_token = cfg["github_token"]
    gh_repo  = cfg.get("github_repo", "ivanmartynov97/telegram-posts")

    items = gh_list("foreign", gh_token, gh_repo)
    files = [it for it in items if it["type"] == "file" and it["name"].endswith(".json") and it["name"] != "state.json"]
    print(f"Найдено {len(files)} постов в foreign/")

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Сессия не авторизована")
        return

    # Назначаем seq по порядку published_at для тех у кого его нет
    posts_with_sha = []
    for it in files:
        post, sha = gh_get_file(it["path"], gh_token, gh_repo)
        posts_with_sha.append((it, post, sha))
    posts_with_sha.sort(key=lambda x: x[1].get("published_at", ""))
    next_seq = 1
    for it, post, sha in posts_with_sha:
        if post.get("seq"):
            next_seq = max(next_seq, post["seq"] + 1)

    for it, post, sha in posts_with_sha:
        changed = False
        if not post.get("seq"):
            post["seq"] = next_seq
            next_seq += 1
            changed = True

        if not post.get("image_url"):
            channel = post.get("channel")
            mid = post.get("message_id")
            print(f"{it['name']}: проверяю оригинал msg {mid} в {channel}...", end=" ")
            try:
                msg = await client.get_messages(channel, ids=mid)
                if msg and getattr(msg, "photo", None):
                    photo_bytes = await client.download_media(msg, file=bytes)
                    if photo_bytes:
                        key = channel.lstrip("@").lower()
                        img_path = f"foreign/images/{key}_{mid}.jpg"
                        image_url = gh_put_binary(img_path, photo_bytes, gh_token, gh_repo, f"Backfill image: {channel} #{mid}")
                        post["image_url"] = image_url
                        changed = True
                        print(f"✅ фото добавлено ({len(photo_bytes)} байт)")
                    else:
                        print("⚠️ download_media вернул пусто")
                elif msg:
                    print("ℹ️ в оригинале нет фото — оставляем как есть")
                else:
                    print("⚠️ оригинальное сообщение не найдено (могло быть удалено)")
            except Exception as e:
                print(f"❌ {e}")

        if changed:
            try:
                gh_put(it["path"], post, sha, gh_token, gh_repo, f"Upgrade: {it['name']}")
                print(f"   💾 сохранено (seq={post['seq']})")
            except Exception as e:
                print(f"   ❌ ошибка сохранения: {e}")

    await client.disconnect()
    print("\n✅ Готово.")

asyncio.run(main())
