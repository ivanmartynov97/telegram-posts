#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/fix_round4_output.txt
{
  echo "=== Git: пуш скрипта фикса live-категорий ==="
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add fix_live_category_prefix.py
  git commit -m "Add script to fix already-scheduled posts that start with category label"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  echo ""

  echo "=== Чиню уже отложенные в Telegram посты с этикеткой категории в начале ==="
  /usr/bin/python3 fix_live_category_prefix.py
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/fix_round4_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
