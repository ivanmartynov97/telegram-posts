#!/bin/bash
# Двойной клик = git push + launchd install + первый запуск early_performance
cd "$(dirname "$0")"

echo "📤 Пушу в GitHub..."
git push origin main

echo "📋 Устанавливаю launchd агент..."
cp com.ivan.early-performance.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.ivan.early-performance.plist 2>/dev/null
launchctl load ~/Library/LaunchAgents/com.ivan.early-performance.plist
echo "✅ early_performance запущен каждые 5 минут"

echo ""
echo "🚀 Запускаю first run..."
python3 early_performance.py

echo ""
echo "✅ Готово!"
read -p "Нажми Enter чтобы закрыть..."
