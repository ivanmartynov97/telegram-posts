#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/refill_channel2_output.txt
{
  echo "=== Пополняем donor-пул foreign/ (грабли) — 5 проходов ==="
  for i in 1 2 3 4 5; do
    echo "--- проход $i ---"
    /usr/bin/python3 grab_foreign.py
    sleep 2
  done
  echo "=== Заполняем queue2 (Рыцарь) до 21 поста из foreign/ ==="
  /usr/bin/python3 weekly_grab_fill.py 21 queue2
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/refill_channel2_output.txt"
echo ""
read -p "Готово. Нажми Enter чтобы закрыть..."
