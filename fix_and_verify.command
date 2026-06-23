#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/fix_and_verify_output.txt
{
  echo "=== Git: коммит и пуш фикса (decommissioned-модель крашила всю генерацию) ==="
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add ai_fill.py index.html
  git commit -m "Fix: decommissioned Groq model (400) was crashing whole generation instead of trying next model/OpenRouter"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  echo ""

  export GROQ_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("groq_key",""))' 2>/dev/null)"
  export OPENROUTER_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("openrouter_key",""))' 2>/dev/null)"

  echo "=== Заполняю queue4 (Умная утка) — 14 AI-постов, тема facts (повтор после фикса) ==="
  /usr/bin/python3 ai_fill.py 14 queue4 facts

  echo ""
  echo "=== Допополняю queue3 (Факт по секрету) ещё 8 постов на случай нехватки ==="
  /usr/bin/python3 ai_fill.py 8 queue3 facts

  echo ""
  echo "=== Сверяю GitHub очереди vs LIVE расписание Telegram ==="
  /usr/bin/python3 inspect_facts_channels.py
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/fix_and_verify_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
