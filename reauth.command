#!/bin/bash
# Переавторизация Telethon с новым api_id
# Двойной клик — удалит старую сессию и создаст новую
cd "$(dirname "$0")"

echo "🔄 Удаляю старую сессию..."
rm -f tg_user_session.session tg_session.session

echo "📱 Запускаю авторизацию с твоим api_id..."
echo "   Введи номер телефона и код из Telegram"
echo ""
python3 setup_telethon.py

if [ -f "tg_user_session.session" ]; then
  echo ""
  echo "✅ Сессия создана! Теперь запускаю early_performance.py..."
  python3 early_performance.py

  echo ""
  echo "📤 Пушу в GitHub..."
  git push origin main

  echo ""
  echo "📋 Устанавливаю launchd агент (каждые 5 минут)..."
  cp com.ivan.early-performance.plist ~/Library/LaunchAgents/
  launchctl unload ~/Library/LaunchAgents/com.ivan.early-performance.plist 2>/dev/null
  launchctl load ~/Library/LaunchAgents/com.ivan.early-performance.plist
  echo "✅ Всё готово!"
else
  echo "❌ Авторизация не удалась — сессия не создана"
fi

read -p "Нажми Enter чтобы закрыть..."
