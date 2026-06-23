#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/run_cleanup_output.txt
{
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add cleanup_queue3.py
  git commit -m "Add cleanup script for leaked historical posts in facts channels"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  echo ""
  /usr/bin/python3 cleanup_queue3.py
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/run_cleanup_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
