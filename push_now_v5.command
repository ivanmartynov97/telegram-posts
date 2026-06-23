#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/push_now_v5_output.txt
{
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add -A
  git commit -m "AI-tab fixes: count-mismatch buffer fix, book-cover removal, hot-model fallback"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  git log --oneline -1
  sleep 3
  curl -s "https://raw.githubusercontent.com/ivanmartynov97/telegram-posts/main/index.html?t=$(date +%s)" -o /tmp/live_index4.html
  echo "bytes: $(wc -c < /tmp/live_index4.html)"
  echo "textPostsAdded marker (should be >=1): $(grep -c textPostsAdded /tmp/live_index4.html)"
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/push_now_v5_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
