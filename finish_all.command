#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/finish_all_output.txt
{
  echo "=== 1. Пополняем donor-пул foreign/ — 8 проходов ==="
  for i in 1 2 3 4 5 6 7 8; do
    echo "--- проход $i ---"
    /usr/bin/python3 grab_foreign.py
    sleep 2
  done
  echo ""
  echo "=== 2. Удаляем дубли по содержанию в канале 1 (История+) ==="
  /usr/bin/python3 dedupe_content_ch1.py
  echo ""
  echo "=== 3. Заполняем queue (История+) недостающие дни 24-28 июня — половина из Граблей ==="
  /usr/bin/python3 weekly_grab_fill.py 14 queue
  echo ""
  echo "=== 4. Заполняем queue2 (Рыцарь) Грабли-половину на неделю (до 21) ==="
  /usr/bin/python3 weekly_grab_fill.py 21 queue2
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/finish_all_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
