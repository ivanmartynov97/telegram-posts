#!/bin/bash
cd "$(dirname "$0")"
export GROQ_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("groq_key",""))' 2>/dev/null)"
OUT=/tmp/fix_groq_and_fill_output.txt
{
  echo "=== 0. Пуш фикса User-Agent (HTTP 403/1010 был Cloudflare-блок, не invalid key) ==="
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add ai_fill.py
  git commit -m "Fix ai_fill.py Groq 403: add browser User-Agent header (Cloudflare bot block)"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  echo ""
  echo "=== 1. queue (История+), 14 постов (history) ==="
  /usr/bin/python3 ai_fill.py 14 queue history
  echo ""
  echo "=== 2. queue2 (Рыцарь), 21 постов (history) ==="
  /usr/bin/python3 ai_fill.py 21 queue2 history
  echo ""
  echo "=== 3. queue3 (Факт по секрету), 14 постов (facts) ==="
  /usr/bin/python3 ai_fill.py 14 queue3 facts
  echo ""
  echo "=== 4. queue4 (Умная утка), 14 постов (facts) ==="
  /usr/bin/python3 ai_fill.py 14 queue4 facts
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/fix_groq_and_fill_output.txt"
unset GROQ_KEY
read -p "Готово. Нажми Enter чтобы закрыть..."
