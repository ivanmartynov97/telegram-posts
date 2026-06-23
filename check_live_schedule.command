#!/bin/bash
cd "$(dirname "$0")"
echo "════════════════════════════════════════"
echo " Смотрю РЕАЛЬНОЕ расписание Telegram (сырой API,"
echo " не обёртка которая недосчитывает). Ничего не меняю."
echo "════════════════════════════════════════"
echo ""
echo "Останавливаю launchd-автопубликатор на время проверки..."
launchctl unload ~/Library/LaunchAgents/com.ivan.auto-publish.plist 2>/dev/null
pkill -f "auto_publish.py" 2>/dev/null
sleep 2
/usr/bin/python3 check_live_schedule.py 2>&1 | tee check_live_schedule_output.txt
echo ""
echo "Включаю автопубликатор обратно..."
launchctl load ~/Library/LaunchAgents/com.ivan.auto-publish.plist 2>/dev/null
echo ""
echo "════════════════════════════════════════"
echo "Готово."
echo "════════════════════════════════════════"
read -p "Нажми Enter чтобы закрыть..."
