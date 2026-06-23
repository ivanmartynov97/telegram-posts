#!/usr/bin/env python3
"""Точечно чинит уже сохранённые посты в queue3/queue4, где слабая модель приклеила
короткую латинскую "подсказку для картинки" (Solar Flare, Murder, Erectalis и т.п.)
в конец текста поста без префикса IMG: — без полной перегенерации (не AI-вызов,
просто текстовая чистка уже сохранённого JSON на GitHub)."""
import json, os, re, base64, ssl, urllib.request

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


def gh_get(path):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        d = json.loads(r.read())
    return json.loads(base64.b64decode(d["content"]).decode()), d["sha"]


def gh_update(path, obj, sha, msg):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    payload = {"message": msg, "sha": sha, "content": base64.b64encode(json.dumps(obj, ensure_ascii=False, indent=2).encode()).decode()}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="PUT",
        headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20, context=ssl_ctx()) as r:
        return json.loads(r.read())


AI_RE = re.compile(r"^\d{8}_\d{6}_\d+\.json$")
LEAK_RE = re.compile(r"\n\s*\n[A-Za-z][A-Za-z\s]{1,40}$")

for qdir in ["queue3", "queue4"]:
    print(f"=== {qdir} ===")
    for it in gh_list(qdir):
        if it.get("type") != "file" or not AI_RE.match(it["name"]):
            continue
        try:
            obj, sha = gh_get(it["path"])
        except Exception as e:
            print(f"  {it['name']}: не смог прочитать ({e})")
            continue
        text = obj.get("text", "")
        if LEAK_RE.search(text):
            fixed = LEAK_RE.sub("", text).strip()
            obj["text"] = fixed
            try:
                gh_update(it["path"], obj, sha, f"Strip leaked image-hint tail from {it['name']}")
                print(f"  ✅ почищен {it['name']}: {fixed[:60]!r}")
            except Exception as e:
                print(f"  ❌ не смог обновить {it['name']}: {e}")
