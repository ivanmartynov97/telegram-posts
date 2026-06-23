#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/push_key_fix_output.txt
{
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add index.html
  git commit -m "Add show/hide toggle for Groq API key field so user can copy it"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  git log --oneline -1
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/push_key_fix_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
