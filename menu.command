#!/bin/bash
cd "$(dirname "$0")"

while true; do
  clear
  echo "════════════════════════════════════════"
  echo "  History+ — меню управления"
  echo "════════════════════════════════════════"
  echo ""
  echo "  1) Push в GitHub (отправить изменения)"
  echo "  2) Грабли — забрать новые посты из @istorian"
  echo "  3) Дозаполнить старые посты Граблей (фото+номера)"
  echo "  4) Заполнить очередь на 2 дня вперёд"
  echo "  5) Проверить Telethon-сессию"
  echo "  6) QR-вход в Telegram (если сессия отвалилась)"
  echo "  7) Auto-publish — поставить очередь в расписание (dry-run сначала)"
  echo "  8) Early performance — собрать охваты за 15 мин"
  echo "  9) Fetch reactions — собрать реакции"
  echo " 10) Установить автозапуск Граблей на Маке (каждые 2 часа)"
  echo " 11) Показать код сессии для GitHub Actions (для облачного автозапуска)"
  echo "  0) Выход"
  echo ""
  read -p "Выбери действие (цифра): " choice

  case $choice in
    1) bash push.command ;;
    2) python3 grab_foreign.py ;;
    3) python3 upgrade_old_foreign.py ;;
    4) python3 fill_two_days.py ;;
    5) python3 check_session.py ;;
    6) python3 setup_qr_login.py ;;
    7)
      python3 auto_publish.py --dry-run
      echo ""
      read -p "Нажми Enter чтобы поставить РЕАЛЬНО (максимум 6), или Ctrl+C чтобы отменить: "
      python3 auto_publish.py
      ;;
    8) python3 early_performance.py ;;
    9) python3 fetch_reactions.py ;;
    10)
      cp com.ivan.grab-foreign.plist ~/Library/LaunchAgents/
      launchctl unload ~/Library/LaunchAgents/com.ivan.grab-foreign.plist 2>/dev/null
      launchctl load ~/Library/LaunchAgents/com.ivan.grab-foreign.plist
      echo "✅ Установлено — Грабли будут пополняться каждые 2 часа (пока Мак включён)"
      ;;
    11) python3 print_session_b64.py ;;
    0) exit 0 ;;
    *) echo "Не понял выбор" ;;
  esac

  echo ""
  read -p "Нажми Enter чтобы вернуться в меню..."
done
