#!/bin/bash
cd "$(dirname "$0")"
export OPENROUTER_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("openrouter_key",""))' 2>/dev/null)"
OUT=/tmp/fix_round9_output.txt
{
  echo "=== Git: пуш фиксов (OpenRouter модели + retry картинок) ==="
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add ai_fill.py index.html fix_missing_images.py
  git commit -m "Fix: update OpenRouter free models (DeepSeek removed); Pollinations retry on 429"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  echo ""

  echo "=== Тест новых OpenRouter моделей ==="
  /usr/bin/python3 - <<'EOF'
import json, urllib.request, ssl, os
KEY = os.environ.get("OPENROUTER_KEY")
def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE; return ctx
for model in ["meta-llama/llama-3.3-70b-instruct:free", "deepseek/deepseek-r1-0528:free", "google/gemma-3-27b-it:free"]:
    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps({"model": model, "messages": [{"role": "user", "content": "Скажи привет по-русски одним словом"}], "max_tokens": 20}).encode(),
            headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "HTTP-Referer": "https://ivanmartynov97.github.io"},
            method="POST")
        with urllib.request.urlopen(req, timeout=20, context=ssl_ctx()) as r:
            body = json.loads(r.read())
            print(f"  ✅ {model}: {body['choices'][0]['message']['content']!r}")
    except urllib.error.HTTPError as e:
        print(f"  ❌ {model}: HTTP {e.code} {e.read()[:120]}")
    except Exception as e:
        print(f"  ❌ {model}: {e}")
EOF
import urllib.error
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/fix_round9_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
