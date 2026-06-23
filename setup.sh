#!/bin/bash
# Переустановка launchd агента для Telegram постинга
# Запустить: bash ~/Claude/Projects/telegram/setup.sh

set -e

PLIST_SRC="$HOME/Claude/Projects/telegram/com.ivan.telegram-relay.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.ivan.telegram-relay.plist"

echo "🔄 Останавливаю старый агент (если был)..."
launchctl unload "$PLIST_DST" 2>/dev/null || true

echo "📋 Копирую обновлённый plist..."
cp "$PLIST_SRC" "$PLIST_DST"

echo "🚀 Загружаю агент..."
launchctl load "$PLIST_DST"

echo ""
echo "✅ Готово! Посты будут публиковаться в 8:00, 10:00, 12:00, 15:00, 18:00, 21:00"
echo ""
echo "📝 Тестирую отправку сейчас..."
echo "Тест: первый пост от автопилота 🚀" > "$HOME/Claude/Projects/telegram/pending_post.txt"
python3 "$HOME/Claude/Projects/telegram/telegram_poster.py"
