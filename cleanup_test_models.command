#!/bin/bash
cd "$(dirname "$0")"
python3 cleanup_test_models.py
echo ""
read -p "Готово. Нажми Enter чтобы закрыть..."
