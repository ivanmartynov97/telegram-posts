#!/bin/bash
cd "$(dirname "$0")"
export GROQ_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("groq_key",""))' 2>/dev/null)"
OUT=/tmp/run_ai_fill_output.txt
{
  echo "=== AI-половина для queue (История+), 14 постов ==="
  /usr/bin/python3 ai_fill.py 14 queue
  echo ""
  echo "=== AI-половина для queue2 (Рыцарь), 21 постов ==="
  /usr/bin/python3 ai_fill.py 21 queue2
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/run_ai_fill_output.txt"
unset GROQ_KEY
read -p "Готово. Нажми Enter чтобы закрыть..."
