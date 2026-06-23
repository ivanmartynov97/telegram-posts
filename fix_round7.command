#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/fix_round7_output.txt
{
  echo "=== Git: пуш фикса (копия session-файла, чтобы не конфликтовать с cron) ==="
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add fix_live_category_prefix.py
  git commit -m "Fix: copy session file to avoid sqlite lock contention with cron"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  echo ""

  echo "=== Чиню уже отложенные в Telegram посты с этикеткой категории в начале (round3) ==="
  /usr/bin/python3 fix_live_category_prefix.py
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/fix_round7_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
