#!/bin/bash
cd "$(dirname "$0")"
# Убираем зависшие lock-файлы
rm -f .git/HEAD.lock .git/MERGE_HEAD.lock .git/index.lock 2>/dev/null

echo "=== Создаём чистую историю (orphan) ==="
# Сохраняем email/name для коммита
git config user.email "appletvrussia@gmail.com" 2>/dev/null || true
git config user.name "Ivan" 2>/dev/null || true

# Создаём orphan-ветку без истории
git checkout --orphan clean_main
git add -A
git commit -m "Clean: all files, no secrets in history"

# Заменяем main
git branch -D main 2>/dev/null || true
git branch -m main

# Force push (заменяет историю на GitHub)
git push -f origin main

echo ""
echo "✅ Готово! История очищена, все файлы запушены."
read -p "Нажми Enter чтобы закрыть..."
