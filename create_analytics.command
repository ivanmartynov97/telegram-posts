#!/bin/bash
cd "$(dirname "$0")"
echo "Создаю папку analytics/ на GitHub..."
python3 create_analytics_folder.py
echo ""
read -p "Нажми Enter чтобы закрыть..."
