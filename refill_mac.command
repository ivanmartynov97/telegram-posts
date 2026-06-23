#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/refill_mac_output.txt
{
  echo "=== Пополняем donor-пул foreign/ — несколько проходов ==="
  for i in 1 2 3 4 5 6; do
    echo "--- проход $i ---"
    /usr/bin/python3 grab_foreign.py
    sleep 2
  done
  echo "=== Заполняем queue (История+) недостающие дни 24-28 июня ==="
  /usr/bin/python3 weekly_grab_fill.py 14 queue
  echo "=== Заполняем queue2 (Рыцарь) до 21 поста из foreign/ ==="
  /usr/bin/python3 weekly_grab_fill.py 21 queue2
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/refill_mac_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
