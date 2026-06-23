#!/bin/bash
cd "$(dirname "$0")"
export GROQ_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("groq_key",""))' 2>/dev/null)"
OUT=/tmp/retry_facts_output.txt
{
  echo "=== 0. Пуш: кликбейт+10% секс-факты, AI-картинки вместо скучных фото для каналов 3-4 ==="
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add index.html ai_fill.py
  git commit -m "Facts channels: more clickbait tone, 10% spicy facts, AI-generated images instead of plain Wikipedia photos"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  echo ""
  echo "=== 1. Дозаполняем queue2 (Рыцарь) — 4 поста, выпавшие из-за 409 Conflict ==="
  /usr/bin/python3 ai_fill.py 4 queue2 history
  echo ""
  echo "=== 2. queue4 (Умная утка), 14 постов (facts, retry после лимита Groq) ==="
  /usr/bin/python3 ai_fill.py 14 queue4 facts
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/retry_facts_output.txt"
unset GROQ_KEY
read -p "Готово. Нажми Enter чтобы закрыть..."
