#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/push_final_output.txt
{
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add -A
  git commit -m "Fix emoji-thumbnail regex (Extended_Pictographic instead of single-codepoint Emoji)"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  git log --oneline -1
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/push_final_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
