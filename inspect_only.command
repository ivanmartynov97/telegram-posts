#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/inspect_only_output.txt
{
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add inspect_facts_channels.py
  git commit -m "Make inspect_facts_channels.py resilient to per-item read errors"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  echo ""
  /usr/bin/python3 inspect_facts_channels.py
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/inspect_only_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
