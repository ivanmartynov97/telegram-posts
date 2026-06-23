#!/usr/bin/env python3
"""Считает сколько AI-постов (формат YYYYMMDD_HHMMSS_NNNNNN.json от ai_fill.py)
уже лежит в queue2/queue4 — чтобы дозаполнить именно недостающее, а не дублировать."""
import json, os, re, ssl, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, "config.json")) as f:
    cfg = json.load(f)
GH_TOKEN = cfg["github_token"]
GH_REPO = "ivanmartynov97/telegram-posts"


def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def gh_list(path):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"})
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
            return json.loads(r.read())
    except Exception:
        return []


AI_RE = re.compile(r"^\d{8}_\d{6}_\d+\.json$")

for qdir in ["queue2", "queue4"]:
    items = gh_list(qdir)
    ai_count = sum(1 for it in items if it.get("type") == "file" and AI_RE.match(it["name"]))
    total = sum(1 for it in items if it.get("type") == "file" and it["name"].endswith(".json"))
    print(f"{qdir}: всего={total} AI-постов={ai_count}")
