#!/bin/bash
cd "$(dirname "$0")"
{
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add index.html
  git commit -m "Fix AI-tab count mismatch: search images for full candidate buffer, not just first N"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  git log --oneline -1
  curl -s "https://raw.githubusercontent.com/ivanmartynov97/telegram-posts/main/index.html?t=$(date +%s)" -o /tmp/live_index2.html
  echo "bytes: $(wc -c < /tmp/live_index2.html)"
  echo "textPostsAdded marker (should be >=1): $(grep -c textPostsAdded /tmp/live_index2.html)"
} > push_now_v3_output.txt 2>&1
cat push_now_v3_output.txt
read -p "Готово. Нажми Enter чтобы закрыть..."
