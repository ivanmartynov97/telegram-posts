#!/bin/bash
# refill_facts.command — очищает queue3/queue4 (Telegram + GitHub) и генерирует
# новые факты через Wikipedia-картинки без AI-мусора.
cd "$(dirname "$0")"

export GROQ_KEY="$(python3 -c "import json; d=json.load(open('config.json')); print(d.get('groq_key',''))" 2>/dev/null)"
export OPENROUTER_KEY="$(python3 -c "import json; d=json.load(open('config.json')); print(d.get('openrouter_key',''))" 2>/dev/null)"

if [ -z "$GROQ_KEY" ]; then
    echo "❌ groq_key не найден в config.json"
    read -p "Нажми Enter чтобы закрыть..."
    exit 1
fi

echo "╔══════════════════════════════════════════════════╗"
echo "║  Шаг 1: Очистка Telegram + GitHub (queue3/queue4) ║"
echo "╚══════════════════════════════════════════════════╝"
python3 clear_facts_channels.py
echo ""

echo "╔══════════════════════════════════════╗"
echo "║  Шаг 2: Генерация фактов для queue3  ║"
echo "╚══════════════════════════════════════╝"
python3 ai_fill.py 60 queue3 facts
echo ""

echo "╔══════════════════════════════════════╗"
echo "║  Шаг 3: Генерация фактов для queue4  ║"
echo "╚══════════════════════════════════════╝"
python3 ai_fill.py 60 queue4 facts
echo ""

echo "╔══════════════════════════════════════════════════════╗"
echo "║  Шаг 4: Постановка в расписание Telegram (5 прогонов) ║"
echo "╚══════════════════════════════════════════════════════╝"
for i in 1 2 3 4 5 6 7 8 9 10; do
    echo "--- Прогон $i/10 ---"
    python3 auto_publish.py
    if [ $i -lt 10 ]; then sleep 5; fi
done

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Готово! Факты обновлены.                             ║"
echo "╚══════════════════════════════════════════════════════╝"
read -p "Нажми Enter чтобы закрыть..."
