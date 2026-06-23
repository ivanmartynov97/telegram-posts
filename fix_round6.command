#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/fix_round6_output.txt
{
  echo "=== Повтор фикса live-категорий (сессия была заблокирована конкурентным процессом) ==="
  for i in 1 2 3 4 5; do
    echo "--- попытка $i ---"
    /usr/bin/python3 fix_live_category_prefix.py
    if [ $? -eq 0 ]; then
      break
    fi
    sleep 8
  done
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/fix_round6_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
