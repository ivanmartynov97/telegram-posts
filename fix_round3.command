#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/fix_round3_output.txt
{
  echo "=== Git: пуш фиксов (запрет 'Категория:' в начале + промпт-усиление) ==="
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add ai_fill.py index.html fix_missing_images.py
  git commit -m "Fix: forbid category-label prefix in facts posts; patch missing images"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  echo ""

  echo "=== Проверяю и чиню queue3/queue4: отсутствующие картинки + 'Категория:' в начале ==="
  /usr/bin/python3 fix_missing_images.py

  echo ""
  echo "=== Финальная сверка: GitHub очереди vs LIVE расписание Telegram ==="
  /usr/bin/python3 inspect_facts_channels.py
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/fix_round3_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
