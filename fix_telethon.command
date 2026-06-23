#!/bin/bash
cd "$(dirname "$0")"
echo "════════════════════════════════════════"
echo " Чиню автопубликацию: модуль telethon пропал из"
echo " окружения /usr/bin/python3 (того, что запускает launchd)."
echo "════════════════════════════════════════"
echo ""
echo "Переустанавливаю telethon..."
/usr/bin/python3 -m pip install --user --upgrade telethon

echo ""
echo "Проверяю, что теперь импортируется:"
/usr/bin/python3 -c "import telethon; print('✅ telethon OK, версия', telethon.__version__)"

echo ""
echo "Перезагружаю автозапуск (launchd агент)..."
launchctl unload ~/Library/LaunchAgents/com.ivan.auto-publish.plist 2>/dev/null
cp com.ivan.auto-publish.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.ivan.auto-publish.plist

echo ""
echo "Запускаю один раз прямо сейчас, чтобы сразу разгрузить очередь..."
python3 auto_publish.py

echo ""
echo "════════════════════════════════════════"
echo "Готово. Если выше видно 'telethon OK' и посты реально"
echo "ставятся в расписание (без ModuleNotFoundError) — починилось."
echo "════════════════════════════════════════"
read -p "Нажми Enter чтобы закрыть..."
