#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/fix_round10_output.txt
{
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add ai_fill.py index.html config.json
  git commit -m "Feature: per-channel image style (cartoon vs cinematic); clean OpenRouter model list"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/fix_round10_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
