#!/bin/bash
cd "$(dirname "$0")"
echo "════════════════════════════════════════"
echo " ПРИМЕНЯЮ перенос дублей-слотов в реальном расписании Telegram."
echo " Текст и фото постов не меняются — только время."
echo "════════════════════════════════════════"
echo ""
echo "Останавливаю launchd-автопубликатор на время (чтобы не конфликтовать за файл сессии)..."
launchctl unload ~/Library/LaunchAgents/com.ivan.auto-publish.plist 2>/dev/null
pkill -f "python3 auto_publish.py" 2>/dev/null
pkill -f "auto_publish.py" 2>/dev/null
sleep 2
/usr/bin/python3 dedupe_schedule.py --apply
echo ""
echo "Включаю автопубликатор обратно..."
launchctl load ~/Library/LaunchAgents/com.ivan.auto-publish.plist 2>/dev/null
echo ""
echo "════════════════════════════════════════"
echo "Готово."
echo "════════════════════════════════════════"
read -p "Нажми Enter чтобы закрыть..."
