#!/bin/bash
cd "$(dirname "$0")"
rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
echo "Коммитим изменения..."
git add -A
git commit -m "Fix hot model photo filtering (wax/junk exclusion + Openverse), Russian-only prompts, Idea emoji/hook enforcement, calendar auto-refresh, ads stats tab, calendar UI" 2>/dev/null || echo "(нечего коммитить)"
echo "Тянем с GitHub..."
git pull --rebase origin main
echo "Пушим..."
git push origin main
echo ""
read -p "Готово. Нажми Enter чтобы закрыть..."
