#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/openrouter_fill_output.txt
{
  echo "=== Текущее состояние очередей ==="
  /usr/bin/python3 check_counts.py
  echo ""

  echo "=== Git: коммит и пуш фикса (OpenRouter fallback) ==="
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add ai_fill.py index.html check_counts.py
  git commit -m "Add OpenRouter fallback for AI generation when Groq quota is exhausted"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  echo ""

  export GROQ_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("groq_key",""))' 2>/dev/null)"
  export OPENROUTER_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("openrouter_key",""))' 2>/dev/null)"

  echo "=== Допополняю queue2 (Рыцарь) до 21 AI-постов ==="
  /usr/bin/python3 ai_fill.py 4 queue2 history

  echo ""
  echo "=== Заполняю queue4 (Умная утка) — 14 AI-постов, тема facts ==="
  /usr/bin/python3 ai_fill.py 14 queue4 facts

  echo ""
  echo "=== Финальное состояние очередей ==="
  /usr/bin/python3 check_counts.py
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/openrouter_fill_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
