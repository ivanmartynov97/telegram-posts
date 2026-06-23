#!/usr/bin/env python3
"""Диагностика двух жалоб: (1) в мини-аппе у части постов в фактах всё равно не видно
картинки, (2) текст всё ещё выглядит как плохой перевод.
Проверяет: 1) реально ли работает OpenRouter сейчас (приватность включена?), 2) реально
ли грузятся URL картинок Pollinations (мини-апп использует onerror=hide -> если картинка
не загрузится, она просто пропадёт из вида, создавая иллюзию "нет фото" хотя в данных
она есть), 3) полный (не обрезанный) текст последних постов для оценки качества."""
import json, os, time, urllib.request, urllib.error, ssl, base64

BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, "config.json")) as f:
    cfg = json.load(f)
GH_TOKEN = cfg["github_token"]
GH_REPO = "ivanmartynov97/telegram-posts"
GROQ_KEY = cfg.get("groq_key") or os.environ.get("GROQ_KEY")
OPENROUTER_KEY = cfg.get("openrouter_key") or os.environ.get("OPENROUTER_KEY")


def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


print("=== 1) Проверка OpenRouter (работает ли DeepSeek сейчас?) ===")
if not OPENROUTER_KEY:
    print("  ❌ Ключ OpenRouter не найден в config.json/env")
else:
    for model in ["deepseek/deepseek-chat-v3-0324:free", "deepseek/deepseek-r1:free"]:
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps({"model": model, "messages": [{"role": "user", "content": "скажи привет одним словом"}], "max_tokens": 20}).encode(),
                headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json",
                         "HTTP-Referer": "https://ivanmartynov97.github.io", "X-Title": "diagnose"},
                method="POST")
            with urllib.request.urlopen(req, timeout=20, context=ssl_ctx()) as r:
                body = json.loads(r.read())
                print(f"  ✅ {model}: РАБОТАЕТ -> {body['choices'][0]['message']['content']!r}")
        except urllib.error.HTTPError as e:
            print(f"  ❌ {model}: HTTP {e.code} {e.read()[:200]}")
        except Exception as e:
            print(f"  ❌ {model}: {e}")

print("\n=== 2) Проверка реальной загрузки картинок Pollinations из очереди ===")


def gh_list(path):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())


def gh_get(path):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        d = json.loads(r.read())
    return json.loads(base64.b64decode(d["content"]).decode())


for qdir in ["queue3", "queue4"]:
    items = gh_list(qdir)
    print(f"\n--- {qdir} ---")
    for it in items:
        if it.get("type") != "file" or not it["name"].endswith(".json"):
            continue
        obj = gh_get(it["path"])
        img = obj.get("image_url")
        text = obj.get("text", "")
        if not img:
            print(f"  {it['name']}: ❌ НЕТ image_url вообще")
            continue
        t0 = time.time()
        try:
            req = urllib.request.Request(img, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=25, context=ssl_ctx()) as r:
                data = r.read()
                dt = time.time() - t0
                ctype = r.headers.get("Content-Type")
                print(f"  {it['name']}: ✅ загрузилась за {dt:.1f}с, {len(data)} байт, type={ctype}")
        except Exception as e:
            dt = time.time() - t0
            print(f"  {it['name']}: ❌ НЕ ЗАГРУЗИЛАСЬ за {dt:.1f}с ({e}) url={img[:90]}")
        print(f"      текст: {text}")

print("\n=== Готово ===")
