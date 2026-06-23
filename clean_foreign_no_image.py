#!/usr/bin/env python3
"""Удаляет из foreign/ посты без image_url (остались от первого запуска до фикса с фото)."""
import json, os, base64, urllib.request, ssl

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

def gh_get(path):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())

def gh_delete(path, sha, msg):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    payload = {"message": msg, "sha": sha}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="DELETE",
        headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())

items = gh_get("foreign")
files = [it for it in items if it["type"] == "file" and it["name"].endswith(".json") and it["name"] != "state.json"]
print(f"Найдено {len(files)} постов в foreign/")

removed = 0
for it in files:
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{it['path']}"
    req = urllib.request.Request(url, headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        data = json.loads(r.read())
    post = json.loads(base64.b64decode(data["content"]).decode("utf-8"))
    if not post.get("image_url"):
        try:
            gh_delete(it["path"], data["sha"], f"Remove no-image foreign post: {it['name']}")
            print(f"   🗑 удалён {it['name']} (без фото)")
            removed += 1
        except Exception as e:
            print(f"   ❌ ошибка удаления {it['name']}: {e}")
    else:
        print(f"   ✅ оставлен {it['name']} (есть фото)")

print(f"\nГотово: удалено {removed} постов без фото.")
