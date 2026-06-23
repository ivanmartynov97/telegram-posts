#!/bin/bash
cd "$(dirname "$0")"

echo "════════════════════════════════════════"
echo "  ШАГ 1: ТЕСТОВЫЙ ПРОГОН (ничего не отправляется)"
echo "════════════════════════════════════════"
python3 auto_publish.py --dry-run

echo ""
echo "════════════════════════════════════════"
echo "Выше показано что БЫЛО БЫ поставлено в расписание."
echo "Если всё выглядит нормально (разумные даты, нормальный текст) — продолжаем."
echo "Если что-то не так — нажми Ctrl+C прямо сейчас и напиши об этом."
echo "════════════════════════════════════════"
read -p "Нажми Enter чтобы РЕАЛЬНО поставить посты в расписание Telegram (максимум 6 за раз)... "

python3 auto_publish.py

echo ""
echo "════════════════════════════════════════"
echo "Если результат выглядит нормально — теперь можно установить автозапуск."
read -p "Установить launchd агент (запуск каждые 30 минут)? Enter = да, Ctrl+C = нет: "

cp com.ivan.auto-publish.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.ivan.auto-publish.plist 2>/dev/null
launchctl load ~/Library/LaunchAgents/com.ivan.auto-publish.plist
echo "✅ Автозапуск установлен (каждые 30 минут, без запуска прямо сейчас)"

read -p "Готово. Нажми Enter чтобы закрыть..."
