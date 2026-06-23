#!/bin/bash
cd "$(dirname "$0")"
echo "════════════════════════════════════════"
echo " DRY-RUN: ищу посты, случайно поставленные на одно и"
echo " то же время (баг в auto_publish.py, уже исправлен в коде)."
echo " Ничего не меняю, только показываю план переноса."
echo "════════════════════════════════════════"
echo ""
echo "Останавливаю launchd-автопубликатор на время (чтобы не конфликтовать за файл сессии)..."
launchctl unload ~/Library/LaunchAgents/com.ivan.auto-publish.plist 2>/dev/null
pkill -f "python3 auto_publish.py" 2>/dev/null
pkill -f "auto_publish.py" 2>/dev/null
sleep 2
DEDUPE_DEBUG=1 /usr/bin/python3 dedupe_schedule.py
echo ""
echo "Включаю автопубликатор обратно..."
launchctl load ~/Library/LaunchAgents/com.ivan.auto-publish.plist 2>/dev/null
echo ""
echo "════════════════════════════════════════"
echo "Если план выше выглядит разумным — запусти dedupe_apply.command"
echo "════════════════════════════════════════"
read -p "Нажми Enter чтобы закрыть..."
