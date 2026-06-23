#!/usr/bin/env python3
"""Диагностика: почему старые посты (например slot-2026-06-20/21) застряли в
очереди GitHub и не публикуются несмотря на много запусков auto_publish.py с тех пор.
Ничего не меняет, только печатает."""
import json, os, base64, urllib.request
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "config.json")
RIGA_TZ = timezone(timedelta(hours=3))

with open(CONFIG) as f:
    cfg = json.load(f)
gh_token = cfg["github_token"]
gh_repo = cfg.get("github_repo", "ivanmartynov97/telegram-posts")
channels = cfg.get("channels") or [{"channel_id": cfg["channel_id"], "queue_dir": "queue"}]

def gh_headers():
    return {"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"}

def list_queue(qd):
    url = f"https://api.github.com/repos/{gh_repo}/contents/{qd}"
    req = urllib.request.Request(url, headers=gh_headers())
    items = json.loads(urllib.request.urlopen(req, timeout=15).read())
    return sorted([it for it in items if it["type"] == "file" and it["name"].endswith(".json")], key=lambda x: x["name"])

def get_file(path):
    url = f"https://api.github.com/repos/{gh_repo}/contents/{path}"
    req = urllib.request.Request(url, headers=gh_headers())
    data = json.loads(urllib.request.urlopen(req, timeout=15).read())
    post = json.loads(base64.b64decode(data["content"]).decode("utf-8"))
    return post, data["sha"]

now_ts = int(datetime.now(RIGA_TZ).timestamp())
print(f"Сейчас: {datetime.now(RIGA_TZ).strftime('%d.%m %H:%M')}")

for ch in channels:
    qd = ch.get("queue_dir", "queue")
    print(f"\n=== {qd} ===")
    items = list_queue(qd)
    print(f"Файлов: {len(items)}")
    no_sched = 0
    expired = 0
    future = 0
    expired_examples = []
    for it in items:
        try:
            post, sha = get_file(it["path"])
        except Exception as e:
            print(f"  ❌ не смог прочитать {it['name']}: {e}")
            continue
        sa = post.get("scheduled_at")
        text = (post.get("text") or "").strip()
        if not sa:
            no_sched += 1
        else:
            try:
                t = int(datetime.fromisoformat(sa.replace("Z", "+00:00")).timestamp())
                if t > now_ts + 60:
                    future += 1
                else:
                    expired += 1
                    if len(expired_examples) < 5:
                        expired_examples.append((it["name"], sa, len(text), bool(post.get("image_url")), text[:60]))
            except Exception as e:
                print(f"  ⚠️ {it['name']}: плохой scheduled_at {sa!r}: {e}")
    print(f"  без scheduled_at (авто-кандидаты): {no_sched}")
    print(f"  scheduled_at в будущем (ручные, ждут своего часа): {future}")
    print(f"  scheduled_at УЖЕ ПРОШЁЛ (застрявшие!): {expired}")
    for name, sa, tlen, has_img, preview in expired_examples:
        print(f"    пример: {name}  scheduled_at={sa}  text_len={tlen}  image={has_img}  text={preview!r}")
