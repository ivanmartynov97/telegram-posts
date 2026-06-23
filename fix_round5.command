#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/fix_round5_output.txt
{
  echo "=== Git: пуш фикса (delete+resend вместо edit для scheduled-сообщений) ==="
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add fix_live_category_prefix.py
  git commit -m "Fix: edit_message doesn't work on scheduled msgs, use delete+resend"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  echo ""

  echo "=== Чиню уже отложенные в Telegram посты с этикеткой категории в начале (round2) ==="
  /usr/bin/python3 fix_live_category_prefix.py
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/fix_round5_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
