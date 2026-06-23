#!/usr/bin/env python3
"""Диагностика + точечный фикс: проверяет ВСЕ посты в queue3/queue4 (включая не-AI,
любого происхождения) на отсутствие image_url, и для facts-каналов всегда обязан быть
AI-сгенерированный (Pollinations) URL картинки — если его нет, генерирует и патчит
JSON на GitHub без повторного вызова текстовой модели (дёшево и быстро)."""
import json, os, re, base64, ssl, random, urllib.request, urllib.parse

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
    except Exception as e:
        print(f"  (gh_list {path} error: {e})")
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


def fetch_ai_generated_image(query):
    seed = random.randint(0, 999999)
    prompt = f"{query}, vivid, eye-catching, high quality illustration, vibrant colors"
    return f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=800&height=800&seed={seed}&nologo=true"


CATEGORY_RE = re.compile(r"^(\S+\s*)[А-ЯA-Z][а-яёa-zA-Z]{2,16}(?:\s[А-ЯA-Z][а-яёa-zA-Z]{2,16})?:\s+")
LEAK_RE = re.compile(r"\n\s*\n[A-Za-z][A-Za-z\s]{1,40}$")

for qdir in ["queue3", "queue4"]:
    items = gh_list(qdir)
    print(f"=== {qdir}: всего файлов = {len(items)} ===")
    no_image = 0
    fixed = 0
    for it in items:
        if it.get("type") != "file" or not it["name"].endswith(".json"):
            continue
        try:
            obj, sha = gh_get(it["path"])
        except Exception as e:
            print(f"  {it['name']}: не смог прочитать ({e})")
            continue
        text = obj.get("text", "")
        img = obj.get("image_url")
        needs_fix = False
        if not img:
            no_image += 1
            needs_fix = True
        if CATEGORY_RE.match(text) or LEAK_RE.search(text):
            needs_fix = True
        if not needs_fix:
            continue
        new_text = CATEGORY_RE.sub(r"\1", text)
        new_text = LEAK_RE.sub("", new_text).strip()
        new_img = img
        if not new_img:
            # Берём только латинские слова из текста, иначе русский текст в URL ломает Pollinations
            q = " ".join(re.sub(r"[^A-Za-z\s]", "", new_text).split()[:4]) or "interesting fact"
            new_img = fetch_ai_generated_image(q)
        if new_text != text or new_img != img:
            obj["text"] = new_text
            obj["image_url"] = new_img
            try:
                gh_update(it["path"], obj, sha, f"Patch missing image / category-prefix in {it['name']}")
                fixed += 1
                print(f"  ✅ {it['name']}: image={'было' if img else 'ДОБАВЛЕНО'} text={(new_text[:50])!r}")
            except Exception as e:
                print(f"  ❌ {it['name']}: не смог обновить ({e})")
    print(f"  --- без картинки было: {no_image}, всего пофикшено постов: {fixed} ---\n")
