#!/usr/bin/env python3
"""Удаляет исторические посты (формат имени slot-YYYY-MM-DDTHH.json — это формат
авто-пополнения topUpChannelTo42, который до фикса заливал историю в факт-каналы),
которые попали в queue3 по ошибке до фикса. Настоящие факт-посты от ai_fill.py
называются по-другому (YYYYMMDD_HHMMSS_NNNNNN.json) и не трогаются."""
import json, os, base64, ssl, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, "config.json")) as f:
    cfg = json.load(f)
GH_TOKEN = cfg["github_token"]
GH_REPO = "ivanmartynov97/telegram-posts"


def ssl_ctx():
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    return ctx


def gh_list(path):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())


def gh_delete(path, sha, msg):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    body = json.dumps({"message": msg, "sha": sha}).encode()
    req = urllib.request.Request(url, data=body, method="DELETE", headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return r.status


for QDIR in ["queue3", "queue4"]:
    print(f"=== {QDIR} ===")
    items = gh_list(QDIR)
    bad = [it for it in items if it.get("type") == "file" and it["name"].startswith("slot-")]
    print(f"Найдено исторических постов для удаления: {len(bad)}")
    for it in bad:
        try:
            gh_delete(it["path"], it["sha"], f"Remove leaked historical post from {QDIR}: {it['name']}")
            print(f"  ✅ удалён {it['name']}")
        except Exception as e:
            print(f"  ❌ не удалил {it['name']}: {e}")
