#!/bin/bash
cd "$(dirname "$0")"
{
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add -A
  git commit -m "AI-tab fixes + snapshot of any concurrent auto_publish writes" --allow-empty
  git add -A
  git commit -m "second safety commit before pull" --allow-empty
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  git log --oneline -1
  sleep 3
  curl -s "https://raw.githubusercontent.com/ivanmartynov97/telegram-posts/main/index.html?t=$(date +%s)" -o /tmp/live_index3.html
  echo "bytes: $(wc -c < /tmp/live_index3.html)"
  echo "textPostsAdded marker (should be >=1): $(grep -c textPostsAdded /tmp/live_index3.html)"
} > push_now_v4_output.txt 2>&1
cat push_now_v4_output.txt
read -p "Готово. Нажми Enter чтобы закрыть..."
