#!/usr/bin/env python3
"""
cleanup_test_models.py — удаляет тестовые посты категории "горячие модели"
(test_hot_model: true), созданные test_hot_models.py для визуальной проверки.
Фото в них оказались нерелевантными (восковые фигуры/чужие люди/обрезка) —
логика поиска фото исправлена в index.html (Commons-фильтр + Openverse),
а эти тестовые посты нужно убрать, чтобы они не ушли в канал как есть.

Запуск: python3 cleanup_test_models.py
"""
import json, os, base64, urllib.request, ssl

BASE   = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "config.json")

with open(CONFIG) as f:
    cfg = json.load(f)
GH_TOKEN = cfg["github_token"]
GH_REPO  = "ivanmartynov97/telegram-posts"

def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def gh_headers():
    return {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}

def gh_list_queue():
    url = f"https://api.github.com/repos/{GH_REPO}/contents/queue"
    req = urllib.request.Request(url, headers=gh_headers())
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())

def gh_get(path):
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

def main():
    items = [it for it in gh_list_queue() if it["type"] == "file" and it["name"].endswith(".json")]
    removed = 0
    for it in items:
        try:
            post, sha = gh_get(it["path"])
        except Exception as e:
            print(f"⚠️ не смог прочитать {it['name']}: {e}")
            continue
        if post.get("test_hot_model"):
            try:
                gh_delete(it["path"], sha, f"Remove bad test hot model post: {it['name']}")
                print(f"🗑 удалён {it['name']} ({post.get('text','')[:50]})")
                removed += 1
            except Exception as e:
                print(f"❌ не смог удалить {it['name']}: {e}")
    print(f"\nГотово: удалено {removed} тестовых постов.")

if __name__ == "__main__":
    main()
