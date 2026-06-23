#!/bin/bash
cd "$(dirname "$0")"
{
  echo "=== git push status ==="
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add -A
  git commit -m "AI-tab fixes: book-cover image source removal, hot-model relaxed fallback" 2>&1
  git pull --rebase origin main 2>&1
  git push origin main 2>&1
  echo "PUSH_EXIT_CODE=$?"
  echo "=== local HEAD ==="
  git log --oneline -1
  echo "=== live GitHub raw content check ==="
  curl -s "https://raw.githubusercontent.com/ivanmartynov97/telegram-posts/main/index.html?t=$(date +%s)" -o /tmp/live_index.html
  echo "downloaded bytes: $(wc -c < /tmp/live_index.html)"
  echo "fromTelegram count (should be 0): $(grep -c fromTelegram /tmp/live_index.html)"
  echo "tgBadge count (should be 0): $(grep -c tgBadge /tmp/live_index.html)"
  echo "findHotModelImageRelaxed count (should be 3): $(grep -c findHotModelImageRelaxed /tmp/live_index.html)"
  echo "fetchArchiveOrgImage(imgQuery) count (should be 0): $(grep -c 'fetchArchiveOrgImage(imgQuery)' /tmp/live_index.html)"
} > verify_push_output.txt 2>&1
cat verify_push_output.txt
read -p "Готово. Нажми Enter чтобы закрыть..."
