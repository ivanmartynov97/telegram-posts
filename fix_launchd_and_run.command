#!/bin/bash
cd "$(dirname "$0")"
echo "════════════════════════════════════════"
echo " Автопубликатор не запускался с 12:36 — проверяю launchd и"
echo " запускаю обработку очереди вручную прямо сейчас."
echo "════════════════════════════════════════"
echo ""
echo "--- Текущий статус launchd ---"
launchctl list | grep auto-publish
echo "(если выше пусто — задача не загружена вообще)"
echo ""
echo "--- Содержимое plist ---"
cat ~/Library/LaunchAgents/com.ivan.auto-publish.plist
echo ""
echo "--- Перезагружаю задачу ---"
launchctl unload ~/Library/LaunchAgents/com.ivan.auto-publish.plist 2>&1
launchctl load ~/Library/LaunchAgents/com.ivan.auto-publish.plist 2>&1
sleep 1
echo ""
echo "--- Статус после перезагрузки ---"
launchctl list | grep auto-publish
echo ""
echo "--- Запускаю auto_publish.py ВРУЧНУЮ прямо сейчас (обработать backlog) ---"
/usr/bin/python3 auto_publish.py 2>&1 | tee fix_launchd_run_output.txt
echo ""
echo "════════════════════════════════════════"
echo "Готово."
echo "════════════════════════════════════════"
read -p "Нажми Enter чтобы закрыть..."
