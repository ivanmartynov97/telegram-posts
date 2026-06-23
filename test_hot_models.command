#!/bin/bash
cd "$(dirname "$0")"
python3 test_hot_models.py
echo ""
read -p "Готово. Нажми Enter чтобы закрыть..."
