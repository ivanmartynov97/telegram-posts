#!/usr/bin/env python3
"""Сбрасывает foreign/state.json — чтобы grab_foreign.py заново прошёл с начала с новым порогом."""
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

url = f"https://api.github.com/repos/{GH_REPO}/contents/foreign/state.json"
req = urllib.request.Request(url, headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"})
with urllib.request.urlopen(req, timeout=10, context=ssl_ctx()) as r:
    data = json.loads(r.read())
sha = data["sha"]

payload = {
    "message": "Reset foreign state to re-scan from start with lower MIN_CHARS",
    "content": base64.b64encode(json.dumps({}, ensure_ascii=False, indent=2).encode()).decode(),
    "sha": sha,
}
req2 = urllib.request.Request(url, data=json.dumps(payload).encode(), method="PUT",
    headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"})
with urllib.request.urlopen(req2, timeout=10, context=ssl_ctx()) as r:
    print("✅ state.json сброшен")
