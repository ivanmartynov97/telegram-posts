#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/redo_facts_output.txt
{
  echo "=== Git: пуш фиксов (приоритет качества моделей + гарантия картинки) ==="
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add ai_fill.py index.html redo_facts.py
  git commit -m "Fix: prioritize OpenRouter/DeepSeek over weak Groq models for quality; always generate an image for facts posts even without IMG: line"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  echo ""

  echo "=== Удаляю все старые AI-посты в queue3/queue4 (часть кривые/без картинки) ==="
  /usr/bin/python3 redo_facts.py
  echo ""

  export GROQ_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("groq_key",""))' 2>/dev/null)"
  export OPENROUTER_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("openrouter_key",""))' 2>/dev/null)"

  echo "=== Пересоздаю queue3 (Факт по секрету) — 14 постов ==="
  /usr/bin/python3 ai_fill.py 14 queue3 facts

  echo ""
  echo "=== Пересоздаю queue4 (Умная утка) — 14 постов ==="
  /usr/bin/python3 ai_fill.py 14 queue4 facts

  echo ""
  echo "=== ПОЛНЫЙ текст всех новых постов для проверки качества ==="
  /usr/bin/python3 - <<'PYEOF'
import json, ssl, urllib.request, base64
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
with open("config.json") as f:
    cfg = json.load(f)
TOKEN = cfg["github_token"]
REPO = "ivanmartynov97/telegram-posts"
def gh_list(path):
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/contents/{path}", headers={"Authorization": f"token {TOKEN}"})
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        return json.loads(r.read())
def gh_get(path):
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/contents/{path}", headers={"Authorization": f"token {TOKEN}"})
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        d = json.loads(r.read())
    return json.loads(base64.b64decode(d["content"]).decode())
import re
AI_RE = re.compile(r"^\d{8}_\d{6}_\d+\.json$")
for qdir in ["queue3", "queue4"]:
    print(f"\n--- {qdir} ---")
    for it in gh_list(qdir):
        if it.get("type") == "file" and AI_RE.match(it["name"]):
            try:
                obj = gh_get(it["path"])
                img = obj.get("image_url") or "НЕТ КАРТИНКИ"
                print(f"[{it['name']}] {obj.get('text')}\n  img={img[:90]}")
            except Exception as e:
                print(f"[{it['name']}] ОШИБКА ЧТЕНИЯ: {e}")
PYEOF
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/redo_facts_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
