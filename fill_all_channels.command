#!/bin/bash
# Заполняет queue3 и queue4 постами на неделю вперёд:
# 1. Генерирует 14 доп. постов для queue4 (их не хватало)
# 2. Запускает auto_publish.py 5 раз, чтобы все посты попали в расписание Telegram
cd "$(dirname "$0")"

export GROQ_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("groq_key",""))' 2>/dev/null)"
export OPENROUTER_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("openrouter_key",""))' 2>/dev/null)"

echo "╔══════════════════════════════════════════════════════╗"
echo "║  Заполнение queue3 (@fact_po_secretu) + queue4 (@umnaya_utka)  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Шаг 1: Генерируем 14 доп. постов для queue4 (Умная утка) ──
echo "=== ШАГ 1: Генерация 14 постов для queue4 (@umnaya_utka) ==="
/usr/bin/python3 ai_fill.py 14 queue4 facts 2>&1
echo ""
echo "queue4 дополнено."
echo ""

# ── Шаг 2: Запускаем auto_publish.py 5 раз ──
# Каждый раз планирует до 6 постов для каждого канала.
# queue3: 14 постов → 3 запуска (6+6+2)
# queue4: 14+14=28 постов → 5 запусков (6+6+6+6+4)

for i in 1 2 3 4 5; do
  echo "════════════════════════════════════════"
  echo "  auto_publish.py — запуск $i/5"
  echo "════════════════════════════════════════"
  /usr/bin/python3 auto_publish.py 2>&1
  echo ""
  if [ $i -lt 5 ]; then
    echo "  ⏳ Пауза 5 секунд перед следующим запуском..."
    sleep 5
  fi
done

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Готово! Все посты поставлены в расписание Telegram.  ║"
echo "╚══════════════════════════════════════════════════════╝"
unset GROQ_KEY OPENROUTER_KEY
read -p "Нажми Enter чтобы закрыть..."
