#!/usr/bin/env python3
"""Удаляет ВСЕ AI-посты (формат ai_fill.py) из queue3/queue4 — часть из них кривые
(слабая fallback-модель ломала грамматику) и/или без картинки (баг с img_query) —
и печатает что осталось (грабли-посты остаются нетронутыми, удаляются только
AI-посты по паттерну имени)."""
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


def gh_delete(path, sha, msg):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    body = json.dumps({"message": msg, "sha": sha}).encode()
    req = urllib.request.Request(url, data=body, method="DELETE", headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return r.status


AI_RE = re.compile(r"^\d{8}_\d{6}_\d+\.json$")

for qdir in ["queue3", "queue4"]:
    items = gh_list(qdir)
    bad = [it for it in items if it.get("type") == "file" and AI_RE.match(it["name"])]
    print(f"=== {qdir}: удаляю {len(bad)} AI-постов (будут пересозданы) ===")
    for it in bad:
        try:
            gh_delete(it["path"], it["sha"], f"Remove low-quality AI post (grammar/missing image bug) from {qdir}: {it['name']}")
            print(f"  удалён {it['name']}")
        except Exception as e:
            print(f"  не удалил {it['name']}: {e}")
