#!/bin/bash
cd "$(dirname "$0")"
export OPENROUTER_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("openrouter_key",""))' 2>/dev/null)"
OUT=/tmp/diagnose_round2_output.txt
{
  echo "=== Git: пуш диагностического скрипта ==="
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add diagnose_round2.py
  git commit -m "Add diagnostics for image-load reliability + OpenRouter status"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  echo ""

  /usr/bin/python3 diagnose_round2.py
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/diagnose_round2_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
