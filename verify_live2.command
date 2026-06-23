#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/verify_live2_output.txt
{
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  echo "=== Жду 20 сек на случай если auto_publish.py держит lock на сессии ==="
  sleep 20
  for i in 1 2 3 4 5; do
    echo "--- попытка $i ---"
    /usr/bin/python3 inspect_facts_channels.py && break
    sleep 15
  done
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/verify_live2_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
