#!/bin/bash
cd "$(dirname "$0")"
echo "Заполняю канал 2 (queue2/) постами из общего пула Граблей на ~3 дня (до 18 постов)..."
python3 weekly_grab_fill.py 18 queue2
echo ""
read -p "Готово. Нажми Enter чтобы закрыть..."
