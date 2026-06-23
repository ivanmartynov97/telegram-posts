#!/bin/bash
cd "$(dirname "$0")"
rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
git add -A
git commit -m "AI-tab: relevance-checked broad image fallback + clearer empty-result message"
git pull --rebase origin main
git push origin main
echo "DONE_PUSH_V2" > push_now_v2_output.txt
git log --oneline -1 >> push_now_v2_output.txt
read -p "Готово. Нажми Enter чтобы закрыть..."
