#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/fix_all_round2_output.txt
{
  echo "=== Git: пуш фиксов (текст-утечка картинки-подсказки + фото-как-документ) ==="
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add ai_fill.py index.html auto_publish.py patch_leaked_text.py fix_live_photos.py
  git commit -m "Fix: strip leaked image-hint text tail; send images as proper photos not documents"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  echo ""

  echo "=== Чищу уже сохранённые посты с приклеенной 'подсказкой картинки' в тексте ==="
  /usr/bin/python3 patch_leaked_text.py
  echo ""

  echo "=== Чиню уже отложенные в Telegram посты где картинка ушла как файл-документ ==="
  /usr/bin/python3 fix_live_photos.py
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/fix_all_round2_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
