#!/bin/bash
# Пушит свежие фиксы ai_fill.py + index.html на GitHub
cd "$(dirname "$0")"
rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
git add ai_fill.py index.html
git commit -m "Fix: убрать markdown-нумерацию «Пост N» + строгий фолбэк картинок (2 слова минимум)" || echo "(нечего коммитить)"
git pull --rebase origin main 2>&1 | tail -5
git push origin main 2>&1
echo "=== PUSH_EXIT=$? ==="
read -p "Готово. Enter чтобы закрыть..."
