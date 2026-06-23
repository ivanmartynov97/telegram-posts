#!/bin/bash
cd "$(dirname "$0")"
export GROQ_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("groq_key",""))' 2>/dev/null)"
OUT=/tmp/push_and_inspect_output.txt
{
  echo "=== 0. Пуш: фикс авто-пополнения (история больше не льётся в факт-каналы) + клик-байт ==="
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add index.html ai_fill.py inspect_facts_channels.py
  git commit -m "Fix autoWeeklyTopUp leaking history content into facts channels; add fact-slot generator + inspection script"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  echo ""
  echo "=== 1. Диагностика: что реально в queue3/queue4 и в LIVE Telegram расписании ==="
  /usr/bin/python3 inspect_facts_channels.py
  echo ""
  echo "=== 2. Дозаполняем queue2 (Рыцарь) — 4 поста ==="
  /usr/bin/python3 ai_fill.py 4 queue2 history
  echo ""
  echo "=== 3. queue4 (Умная утка), 14 постов (facts, retry) ==="
  /usr/bin/python3 ai_fill.py 14 queue4 facts
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/push_and_inspect_output.txt"
unset GROQ_KEY
read -p "Готово. Нажми Enter чтобы закрыть..."
